from datetime import datetime, timedelta, timezone

import pytest

from engine.market_scan import market_scan, scan_payload
from engine.providers.base import Observation

NOW = datetime(2026, 10, 8, tzinfo=timezone.utc)


def test_scan_observations_remain_auditable_and_future_values_fail():
    bar = Observation(
        "FIXTURE",
        NOW - timedelta(days=1),
        NOW,
        "fixture",
        {"c": 100, "h": 102, "l": 98, "v": 1000},
        "fixture",
    )
    result = scan_payload([bar], NOW)
    assert result["features"]["last_close"] == 100
    assert result["observations"][0]["available_at"] == NOW.isoformat()
    with pytest.raises(ValueError):
        scan_payload([bar], NOW - timedelta(seconds=1))


def test_missing_feed_is_not_counted_as_covered(monkeypatch):
    class Provider:
        def bars(self, *args):
            return []

    class Database:
        rows = []

        def rpc(self, name, payload):
            assert name == "radar_claim_market"
            return [{"symbol": "FIXTURE", "lease_token": "fixture-lease"}]

        def finish_market(self, symbol, lease, payload):
            assert lease == "fixture-lease"
            self.rows.append(payload)
            return True

        def write(self, table, rows):
            assert not rows

    monkeypatch.setattr("engine.market_scan.Nasdaq", Provider)
    db = Database()
    result = market_scan(db)
    assert result["covered"] == 0
    assert result["unavailable"] == 1
    assert db.rows[0]["state"] == "unavailable"
    assert db.rows[0]["sample_size"] == 0
