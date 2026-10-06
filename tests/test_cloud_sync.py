import json
import threading
from http.server import HTTPServer
from urllib.request import urlopen
from urllib.error import HTTPError
from earnings_radar.sources import prepare
from earnings_radar.db import get_conn
from earnings_radar.ingestion import ingest
from earnings_radar.providers.base import Event
from earnings_radar.analysis import process_pending
from earnings_radar.settings import Settings
from earnings_radar.cloud_sync import publish
from web.api._store import Store, StoreError
from web.api.index import handler
import pytest


def test_cloud_export_stable_references_and_no_private_tables(tmp_path):
    path = prepare(tmp_path/'research.db')
    with get_conn(path) as conn:
        ingest(conn, Event('sec', 'filing-1', 'https://www.sec.gov/Archives/test.htm',
                          'AAPL filed 10-Q', '2026-01-01T00:00:00+00:00', ('AAPL',)))
    process_pending(path, Settings())
    class Fake:
        calls = []
        def request(self, table, **kwargs): self.calls.append((table, kwargs))
    fake = Fake(); assert publish(path, fake) == 1
    row = fake.calls[0][1]['rows'][0]
    assert row['id'] == row['analysis']['event_id'] == row['analysis']['confirmed_facts'][0]['evidence_id']
    assert len(row['id']) == 64
    assert 'first_seen_at' not in row  # Database preserves original cloud arrival time.
    assert {c[0] for c in fake.calls} == {'radar_events', 'radar_status'}
    fake2 = Fake(); fake2.calls = []; publish(path, fake2)
    assert fake2.calls[0][1]['rows'][0]['id'] == row['id']


def test_store_rejects_unsafe_project_urls(monkeypatch):
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY','test-secret')
    for url in ('http://project.supabase.co','https://evil.example','https://user@project.supabase.co'):
        monkeypatch.setenv('SUPABASE_URL', url)
        with pytest.raises(StoreError): Store()


def test_api_missing_config_is_actionable_and_does_not_leak_key(monkeypatch):
    monkeypatch.delenv('SUPABASE_URL', raising=False)
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY','do-not-expose')
    server = HTTPServer(('127.0.0.1',0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        with pytest.raises(HTTPError) as exc:
            urlopen(f'http://127.0.0.1:{server.server_port}/api/dashboard')
        assert exc.value.code == 503
        text = exc.value.read().decode(); assert 'do-not-expose' not in text
        assert json.loads(text)['events'] == []
    finally:
        server.shutdown(); server.server_close(); thread.join()
