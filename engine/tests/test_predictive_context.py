from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from engine.implied_archive import eligible_reports
from engine.predictive_context import (
    context_features,
    days_to_report,
    earnings_memory,
    trading_multiples,
)

NOW = datetime(2026, 10, 8, 20, tzinfo=timezone.utc)


def bars(
    count: int, volume: float = 100, high: float = 101, low: float = 99
) -> list[dict]:
    return [{"c": 100, "h": high, "l": low, "v": volume} for _ in range(count)]


def test_conflicting_earnings_dates_leave_the_count_missing():
    events = [
        {
            "report_date": "2026-10-11",
            "date_status": "conflicting",
            "sources": [
                {"source": "Finnhub", "date": "2026-10-11"},
                {"source": "Alpha Vantage", "date": "2026-10-12"},
            ],
        }
    ]
    assert days_to_report(events, NOW) == {
        "days_to_report": None,
        "days_to_report_known": 0,
    }


def test_agreed_report_counts_calendar_days():
    events = [
        {
            "report_date": "2026-10-11",
            "date_status": "estimated",
            "sources": [
                {"source": "Finnhub", "date": "2026-10-11"},
                {"source": "Alpha Vantage", "date": "2026-10-11"},
            ],
        }
    ]
    result = days_to_report(events, NOW)
    assert result["days_to_report"] == 3
    assert result["days_to_report_known"] == 1


def test_volume_and_range_use_the_prior_twenty_sessions():
    history = bars(21)
    history.append({"c": 100, "h": 104, "l": 100, "v": 250})
    result = trading_multiples(history)
    assert result["volume_multiple_20"] == 2.5
    assert result["range_multiple_20"] == 2
    assert result["volume_multiple_20_known"] == 1


def test_short_history_stays_missing():
    result = trading_multiples(bars(10))
    assert result["volume_multiple_20"] is None
    assert result["volume_multiple_20_known"] == 0


def test_earnings_history_cannot_be_used_before_it_was_saved():
    rows = [
        {
            "as_of": (NOW + timedelta(days=1)).isoformat(),
            "payload": {
                "reported_date": "2026-07-22",
                "reported_eps": 2.0,
                "estimated_eps": 1.0,
                "surprise": 1.0,
            },
        }
    ]
    result = earnings_memory(rows, NOW)
    assert result["last_surprise"] is None
    assert result["beat_rate_4"] is None
    assert result["beat_rate_4_known"] == 0


def test_beat_rate_needs_four_saved_quarters():
    rows = []
    for index in range(4):
        rows.append(
            {
                "as_of": (NOW - timedelta(days=1)).isoformat(),
                "payload": {
                    "reported_date": f"2026-0{index + 1}-20",
                    "reported_eps": 2.0,
                    "estimated_eps": 1.0,
                    "surprise": 1.0 if index == 3 else 0.5,
                },
            }
        )
    result = earnings_memory(rows, NOW)
    assert result["last_surprise"] == 1.0
    assert result["beat_rate_4"] == 1
    short = earnings_memory(rows[:3], NOW)
    assert short["last_surprise"] == 0.5
    assert short["beat_rate_4"] is None


def test_implied_move_ignores_a_snapshot_saved_after_the_cutoff():
    implied = [
        {
            "observed_at": (NOW + timedelta(minutes=5)).isoformat(),
            "retrieved_at": (NOW + timedelta(minutes=5)).isoformat(),
            "payload": {"implied_move": 0.08, "report_date": "2026-10-11"},
        }
    ]
    features = context_features([], [], [], implied, {}, NOW)
    assert features["implied_move"] is None
    assert features["implied_move_known"] == 0
    assert features["spy_return_5_known"] == 0


def test_saved_implied_move_matches_the_agreed_report():
    events = [
        {
            "report_date": "2026-10-11",
            "date_status": "estimated",
            "sources": [{"source": "Finnhub", "date": "2026-10-11"}],
        }
    ]
    implied = [
        {
            "observed_at": (NOW - timedelta(hours=1)).isoformat(),
            "retrieved_at": (NOW - timedelta(hours=1)).isoformat(),
            "payload": {"implied_move": 0.08, "report_date": "2026-10-11"},
        }
    ]
    features = context_features(
        bars(22), events, [], implied, {"return_5": 0.01, "rv_60": 0.2}, NOW
    )
    assert features["implied_move"] == 0.08
    assert features["spy_return_5"] == 0.01
    assert features["spy_rv_60_known"] == 1


def test_archive_skips_disagreements_and_keeps_the_soonest_report():
    events = [
        {
            "symbol": "LATER",
            "report_date": "2026-11-01",
            "date_status": "estimated",
            "sources": [{"source": "Finnhub", "date": "2026-11-01"}],
        },
        {
            "symbol": "SPLIT",
            "report_date": "2026-10-20",
            "date_status": "conflicting",
            "sources": [
                {"source": "Finnhub", "date": "2026-10-20"},
                {"source": "Alpha Vantage", "date": "2026-10-21"},
            ],
        },
        {
            "symbol": "SOON",
            "report_date": "2026-10-12",
            "date_status": "estimated",
            "sources": [{"source": "Alpha Vantage", "date": "2026-10-12"}],
        },
    ]
    assert eligible_reports(
        events, NOW.astimezone(ZoneInfo("America/New_York")).date()
    ) == [
        ("SOON", "2026-10-12"),
        ("LATER", "2026-11-01"),
    ]
