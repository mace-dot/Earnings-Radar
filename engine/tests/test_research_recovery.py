from datetime import datetime, timezone

import pytest

from engine.research_readiness import check
from engine.run import calendar_symbols

NOW = datetime(2026, 10, 14, 23, tzinfo=timezone.utc)


def test_recovery_rejects_incomplete_coverage():
    class Database:
        def read(self, table, query):
            assert query["sample_size"] == "gte.61"
            assert query["last_session"].startswith("gte.")
            return []

    with pytest.raises(RuntimeError, match="Insufficient"):
        check(Database(), NOW)


def test_recovery_accepts_usable_partial_coverage():
    class Database:
        def read(self, table, query):
            return [{"symbol": f"FIXTURE{i}"} for i in range(100)]

    assert check(Database(), NOW) == 100


def test_deep_research_is_bounded_and_pending_requests_take_priority():
    class Database:
        def pages(self, table, query):
            if table == "score_queue":
                assert query["state"] == "in.(queued,running)"
                return [{"symbol": "REQUEST_FIXTURE"}]
            return [{"symbol": f"FIXTURE{i:04}"} for i in range(1000)]

        def read(self, table, query):
            assert table == "lines" and query["expires_at"].startswith("gte.")
            return [{"symbol": "RECENT_FIXTURE"}]

    symbols = calendar_symbols(Database(), NOW)
    assert len(symbols) == 300
    assert symbols[:2] == ["REQUEST_FIXTURE", "RECENT_FIXTURE"]
    assert len(set(symbols)) == 300
