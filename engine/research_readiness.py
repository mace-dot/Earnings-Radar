"""Gate partial bootstrap recovery on actual usable, recent history."""

from datetime import datetime, timezone
from typing import Any

from engine.providers.daily_history import FEED, recent_sessions
from engine.store import Store


def check(store: Any, now: datetime, minimum: int = 100) -> int:
    sessions = recent_sessions(now)
    cutoff = sessions[-3]
    rows = store.read(
        "market_coverage",
        {
            "select": "symbol",
            "state": "eq.covered",
            "feed": f"eq.{FEED}",
            "sample_size": "gte.61",
            "last_session": f"gte.{cutoff}",
            "limit": str(minimum),
        },
    )
    if len(rows) < minimum:
        raise RuntimeError(
            "Insufficient recent archived coverage; research recovery blocked"
        )
    return len(rows)


if __name__ == "__main__":
    print(
        "Usable recent histories verified:", check(Store(), datetime.now(timezone.utc))
    )
