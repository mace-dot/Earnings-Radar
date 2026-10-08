from datetime import datetime, timedelta, timezone

import pytest

from engine.history_cache import restore, volume_count

NOW = datetime(2026, 10, 8, 14, tzinfo=timezone.utc)


class Database:
    rows = []

    def pages(self, table, query):
        return [
            {
                "symbol": "FIXTURE",
                "payload": {
                    "observations": [
                        {
                            "observed_at": (NOW - timedelta(days=1)).isoformat(),
                            "available_at": NOW.isoformat(),
                            "source": "fixture-source",
                            "feed": "fixture-feed",
                            "values": {"t": "2026-10-07", "c": 100, "v": 1000},
                        }
                    ]
                },
            }
        ]

    def write(self, table, rows, immutable=False):
        assert table == "daily_bars" and immutable
        self.rows = rows


def test_cache_restoration_preserves_source_and_original_available_time():
    database = Database()
    result = restore(database, ["FIXTURE"], NOW + timedelta(hours=1))
    assert result["bars"] == 1
    assert database.rows[0]["available_at"] == NOW.isoformat()
    assert database.rows[0]["source"] == "fixture-source"
    assert database.rows[0]["feed"] == "fixture-feed"


def test_future_cached_observation_cannot_become_a_backend_input():
    database = Database()
    with pytest.raises(ValueError):
        restore(database, ["FIXTURE"], NOW - timedelta(seconds=1))


def test_integral_cached_float_volume_is_serialized_as_integer():
    assert volume_count(149588.0) == 149588
    assert isinstance(volume_count(149588.0), int)
    assert volume_count(None) is None


@pytest.mark.parametrize("value", [1.5, -1, float("inf"), float("nan")])
def test_invalid_cached_volume_is_not_rounded_or_invented(value):
    with pytest.raises(ValueError):
        volume_count(value)
