from datetime import datetime,timezone,timedelta
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from earnings_radar import config,db
from earnings_radar.sources import prepare
from earnings_radar.ingestion import ingest
from earnings_radar.providers.base import Event
from earnings_radar.analysis import process_pending
from earnings_radar.settings import Settings

APP=Path(__file__).resolve().parents[1]/'app.py'

def test_research_pages_and_persistent_review(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'DB_PATH',tmp_path/'app.db')
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'app.db')
    monkeypatch.setenv('RADAR_RESEARCH_DB_PATH',str(tmp_path/'research.db'))
    path=prepare();now=datetime.now(timezone.utc)
    with db.get_conn(path) as c:ingest(c,Event('fixture','1','https://www.sec.gov/a','AAPL filed 10-Q',now.isoformat(),('AAPL',),access_category='fixture'),now=now,replay=True)
    process_pending(path,Settings())
    app=AppTest.from_file(str(APP),default_timeout=30).run()
    assert not app.exception,app.exception
    assert any('weekly picks' in m.value.lower() for m in app.markdown)
    next(b for b in app.button if b.label=='Evaluate & log').click().run()
    assert not app.exception,app.exception
    with db.get_conn(path) as c:
        payload=c.execute('SELECT payload FROM evaluations').fetchone()[0]
        assert 'no_verified_upcoming_earnings_schedule' in payload
    next(b for b in app.button if b.label=='Mark reviewed').click().run()
    assert not app.exception,app.exception
    with db.get_conn(path) as c:assert c.execute('SELECT read_at FROM alerts').fetchone()[0]
    for page in ['Opportunities','Earnings','Systemic Risk','Evidence','Connections','Import','Option quotes','Research notes','Export packet','Paper journal','About']:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception,(page,app.exception)
    # The research board must never display real alerts under Demo mode.
    app.sidebar.selectbox[0].set_value('Demo').run()
    app.sidebar.radio[0].set_value('Today').run()
    assert any('Switch to Research mode' in m.value for m in app.info)


def test_dashboard_export_share_selection(tmp_path,monkeypatch):
    from earnings_radar.export import build_research_packet
    from earnings_radar.quote_selection import select_quote
    from test_integrity import EVENT,quote
    monkeypatch.setattr(config,'DB_PATH',tmp_path/'app.db');monkeypatch.setattr(db,'DB_PATH',tmp_path/'app.db');db.DB_OVERRIDE.set(None)
    now=datetime.now(timezone.utc)
    db.init_db()
    q=quote();q.update(quote_timestamp=now.isoformat(),expiration=(now+timedelta(days=30)).date().isoformat())
    stamp=(now+timedelta(days=30)).strftime('%y%m%d')
    q.update(call_contract_id='AAA'+stamp+'C00100000',put_contract_id='AAA'+stamp+'P00100000')
    event={**EVENT,'earnings_date':(now+timedelta(days=7)).date().isoformat()}
    with db.get_conn() as c:
        db.insert_earnings_event(c,event)
        qid=db.insert_option_quote(c,q)
        rows=db.fetch_all(c,'SELECT * FROM option_quotes')
    assert select_quote(event,rows)['id']==qid
    assert f'Selected quote ID:** {qid}' in build_research_packet('AAA')
