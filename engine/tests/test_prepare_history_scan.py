from datetime import datetime, timezone

import pytest

from engine.prepare_history_scan import prepare
from engine.providers.daily_history import recent_sessions

NOW = datetime(2026, 10, 8, 17, tzinfo=timezone.utc)


class Database:
    def __init__(self, sessions):
        self.sessions = sessions
        self.patched = False

    def read(self, *args):
        return [{"session_date": day} for day in self.sessions]

    def _request(self, table, **kwargs):
        assert table == "market_coverage"
        assert "lease_until" in kwargs["params"]["or"]
        self.patched = True


def test_partial_archive_does_not_reset_coverage():
    database = Database(recent_sessions(NOW)[-3:])
    with pytest.raises(RuntimeError, match="not archived"):
        prepare(database, NOW)
    assert not database.patched


def test_complete_archive_refreshes_only_unleased_coverage():
    database = Database(recent_sessions(NOW))
    assert prepare(database, NOW) == 61
    assert database.patched
