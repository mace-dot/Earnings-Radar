from datetime import datetime
from zoneinfo import ZoneInfo

from engine.schedule import pending_jobs


def test_late_start_still_runs_grading():
    now = datetime(2026, 10, 8, 17, 53, tzinfo=ZoneInfo("America/New_York"))
    jobs = pending_jobs(now, [])
    assert "grade" in jobs
    assert jobs.index("implied_archive") < jobs.index("prices")
    runs = [
        {"job": job, "as_of": now.isoformat(), "status": "completed"}
        for job in pending_jobs(now, [])
    ]
    assert not pending_jobs(now, runs)


def test_failed_job_is_retried_and_future_slot_not_run_early():
    now = datetime(2026, 10, 8, 12, 5, tzinfo=ZoneInfo("America/New_York"))
    assert "grade" not in pending_jobs(now, [])
    assert "context" in pending_jobs(
        now, [{"job": "context", "as_of": now.isoformat(), "status": "failed"}]
    )


def test_eastern_dst_is_used():
    now = datetime(2026, 11, 2, 17, 5, tzinfo=ZoneInfo("UTC"))
    assert "context" in pending_jobs(now, [])
    assert "grade" not in pending_jobs(now, [])


def test_usable_calendar_partial_does_not_retry_forever_for_optional_provider():
    now = datetime(2026, 10, 8, 12, 5, tzinfo=ZoneInfo("America/New_York"))
    runs = [
        {
            "job": "calendar",
            "as_of": now.isoformat(),
            "status": "partial",
            "payload": {"events": 100},
        }
    ]
    assert "calendar" not in pending_jobs(now, runs)
    runs[0]["payload"] = {"events": 0}
    assert "calendar" in pending_jobs(now, runs)


def test_evening_history_rollover_refreshes_prices_before_validation():
    from engine.schedule import due_jobs

    now = datetime(2026, 10, 8, 20, 0, tzinfo=ZoneInfo("America/New_York"))
    assert due_jobs(now) == ["prices", "score", "validate"]
