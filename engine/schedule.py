"""DST-aware scheduled dispatcher; duplicate UTC cron hours are intentional."""

import os
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from engine.store import Store

SLOTS = {
    (6, 0): ["universe", "sectors"],
    (6, 15): ["calendar"],
    (18, 0): ["calendar"],
    (9, 45): ["context", "score"],
    (12, 0): ["context", "score"],
    (15, 30): ["context", "score"],
    (17, 30): ["prices", "score"],
    (17, 45): ["grade"],
    (20, 0): ["score"],
}


def due_jobs(now: datetime) -> list[str]:
    eastern = now.astimezone(ZoneInfo("America/New_York"))
    if eastern.weekday() >= 5:
        return []
    return SLOTS.get((eastern.hour, eastern.minute), [])


def pending_jobs(now: datetime, runs: list[dict]) -> list[str]:
    """Catch up when GitHub starts late; do not require an exact cron minute."""
    eastern = now.astimezone(ZoneInfo("America/New_York"))
    if eastern.weekday() >= 5:
        return []
    due = {}
    for (hour, minute), jobs in sorted(SLOTS.items()):
        slot = eastern.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if slot <= eastern:
            for job in jobs:
                due[job] = slot
    completed = {}
    for run in runs:
        usable_partial = run["status"] == "partial" and bool(
            run.get("payload", {}).get("events")
            or run.get("payload", {}).get("processed_symbols")
        )
        if run["status"] != "completed" and not usable_partial:
            continue
        stamp = datetime.fromisoformat(run["as_of"].replace("Z", "+00:00"))
        if run["job"] not in completed or stamp > completed[run["job"]]:
            completed[run["job"]] = stamp
    return [
        job
        for job in (
            "universe",
            "sectors",
            "calendar",
            "prices",
            "context",
            "score",
            "grade",
        )
        if job in due and (job not in completed or completed[job] < due[job])
    ]


def main() -> None:
    job = os.getenv("MANUAL_JOB")
    if job:
        jobs = [job]
    else:
        now = datetime.now(ZoneInfo("UTC"))
        runs = Store().read(
            "engine_runs",
            {
                "select": "job,as_of,status,payload",
                "as_of": f"gte.{now.astimezone(ZoneInfo('America/New_York')).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()}",
                "order": "as_of.desc",
                "limit": "1000",
            },
        )
        jobs = ["queue", "market_scan", *pending_jobs(now, runs)]
    if not jobs:
        print("No job due at this Eastern time")
    for item in jobs:
        subprocess.run([sys.executable, "-m", "engine.run", item], check=True)


if __name__ == "__main__":
    main()
