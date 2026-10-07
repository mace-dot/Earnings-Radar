"""DST-aware scheduled dispatcher; duplicate UTC cron hours are intentional."""

import os
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo


def due_jobs(now: datetime) -> list[str]:
    eastern = now.astimezone(ZoneInfo("America/New_York"))
    if eastern.weekday() >= 5:
        return []
    return {
        (6, 0): ["universe", "sectors"],
        (6, 15): ["calendar"],
        (18, 0): ["calendar"],
        (9, 45): ["context", "score"],
        (12, 0): ["context", "score"],
        (15, 30): ["context", "score"],
        (17, 30): ["prices", "score"],
        (20, 0): ["score"],
    }.get((eastern.hour, eastern.minute), [])


def main() -> None:
    job = os.getenv("MANUAL_JOB")
    jobs = [job] if job else ["queue", *due_jobs(datetime.now(ZoneInfo("UTC")))]
    if not jobs:
        print("No job due at this Eastern time")
    for item in jobs:
        subprocess.run([sys.executable, "-m", "engine.run", item], check=True)


if __name__ == "__main__":
    main()
