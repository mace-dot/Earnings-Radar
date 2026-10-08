"""Refresh the directory only after the shared feature window is available."""

from datetime import datetime, timezone

from engine.providers.daily_history import FEED, recent_sessions
from engine.store import Store


def prepare(store: Store, now: datetime) -> int:
    expected = [day for day in recent_sessions(now) if day < now.date().isoformat()][
        -61:
    ]
    archived = {
        row["session_date"]
        for row in store.read(
            "market_history_days", {"feed": f"eq.{FEED}", "select": "session_date"}
        )
    }
    # Basic accounts expose completed history on the following UTC date.
    if len(expected) < 61 or not set(expected).issubset(archived):
        raise RuntimeError(
            "Complete recent feature window is not archived; refresh deferred"
        )
    store._request(
        "market_coverage",
        method="PATCH",
        params={"or": f"(lease_until.is.null,lease_until.lt.{now.isoformat()})"},
        json={"next_attempt_at": now.isoformat()},
    )
    return len(expected)


if __name__ == "__main__":
    print("History sessions verified:", prepare(Store(), datetime.now(timezone.utc)))
