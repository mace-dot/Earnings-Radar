from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from engine.alpha_budget import calendar_collected, choose_symbols, plan, requests_used
from engine.providers.alpha_vantage import QuotaExceeded, normalize_earnings
from engine.schedule import pending_jobs

NOW = datetime(2026, 10, 8, 15, tzinfo=timezone.utc)
DAY = "2026-10-08"


def _security(symbol: str, asset: str = "common_stock") -> dict:
    return {"symbol": symbol, "asset_type": asset}


def test_legacy_calendar_run_counts_as_one_request():
    runs = [
        {
            "job": "calendar",
            "as_of": NOW.isoformat(),
            "status": "completed",
            "payload": {"events": 10, "provider_errors": []},
        }
    ]
    assert requests_used(runs, DAY) == 1
    assert calendar_collected(runs, DAY)


def test_plan_keeps_one_spare_and_one_calendar_call():
    events = [{"symbol": f"T{i:02d}", "report_date": "2026-10-20"} for i in range(30)]
    securities = [_security(event["symbol"]) for event in events]
    budget = plan(NOW, [], events, securities, [], [])
    assert budget["calendar"] is True
    assert len(budget["symbols"]) == 23
    assert budget["used"] + 1 + len(budget["symbols"]) == 24


def test_soonest_unfetched_report_comes_first():
    events = [
        {"symbol": "LATER", "report_date": "2026-11-15"},
        {"symbol": "SOON", "report_date": "2026-10-12"},
    ]
    securities = [_security("LATER"), _security("SOON")]
    assert choose_symbols(NOW, events, securities, [], {}, 2) == ["SOON", "LATER"]


def test_saved_pre_report_history_is_not_downloaded_again():
    events = [{"symbol": "AAPL", "report_date": "2026-10-20"}]
    histories = {
        "AAPL": {
            "fetched_at": "2026-10-01T12:00:00+00:00",
            "latest_reported": "2026-07-30",
            "empty": False,
        }
    }
    assert choose_symbols(NOW, events, [_security("AAPL")], [], histories, 5) == []


def test_passed_report_is_refreshed_when_the_result_is_not_saved():
    events = [{"symbol": "AAPL", "report_date": "2026-10-06"}]
    histories = {
        "AAPL": {
            "fetched_at": "2026-10-01T12:00:00+00:00",
            "latest_reported": "2026-07-30",
            "empty": False,
        }
    }
    assert choose_symbols(NOW, events, [_security("AAPL")], [], histories, 5) == [
        "AAPL"
    ]


def test_missing_estimate_stays_missing_and_limit_stops_the_batch():
    retrieved = datetime(2026, 10, 8, tzinfo=timezone.utc)
    rows = normalize_earnings(
        "AAPL",
        {
            "quarterlyEarnings": [
                {
                    "fiscalDateEnding": "2026-06-30",
                    "reportedDate": "2026-07-30",
                    "reportedEPS": "1.25",
                    "estimatedEPS": "None",
                    "surprise": None,
                    "surprisePercentage": "",
                }
            ]
        },
        retrieved,
    )
    assert rows[0]["payload"]["reported_eps"] == 1.25
    assert rows[0]["payload"]["estimated_eps"] is None
    with pytest.raises(QuotaExceeded):
        normalize_earnings(
            "AAPL",
            {
                "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 25 requests per day."
            },
            retrieved,
        )


def test_alpha_scan_waits_until_the_morning_slot_and_does_not_repeat():
    before = datetime(2026, 10, 8, 6, 10, tzinfo=ZoneInfo("America/New_York"))
    assert "alpha_scan" not in pending_jobs(before, [])
    due = datetime(2026, 10, 8, 6, 20, tzinfo=ZoneInfo("America/New_York"))
    jobs = pending_jobs(due, [])
    assert jobs.index("calendar") < jobs.index("alpha_scan")
    done = [
        {
            "job": "calendar",
            "as_of": due.isoformat(),
            "status": "completed",
            "payload": {"events": 1},
        },
        {
            "job": "alpha_scan",
            "as_of": due.isoformat(),
            "status": "partial",
            "payload": {
                "budget_complete": True,
                "provider_errors": [{"status": "quota"}],
            },
        },
    ]
    assert "alpha_scan" not in pending_jobs(due, done)
