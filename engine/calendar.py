"""Reconcile estimated event dates; agreement does not imply official confirmation."""

from collections import defaultdict
from datetime import datetime
from typing import Any

from engine.providers.base import Observation


def reconcile(observations: list[Observation], as_of: datetime) -> list[dict[str, Any]]:
    grouped: dict[str, list[Observation]] = defaultdict(list)
    for item in observations:
        item.at(as_of)
        grouped[item.symbol].append(item)
    result = []
    for symbol, entries in grouped.items():
        dates = {entry.values["date"] for entry in entries}
        # Keep conflicts visible; no silent averaging of event dates.
        latest = max(entries, key=lambda entry: entry.available_at)
        date = latest.values["date"]
        result.append(
            {
                "id": f"{symbol}:{date}",
                "symbol": symbol,
                "report_date": date,
                "timing": latest.values.get("hour") or "unknown",
                "date_status": "conflicting" if len(dates) > 1 else "estimated",
                "sources": [
                    {
                        "source": entry.source,
                        "as_of": entry.available_at.isoformat(),
                        "date": entry.values["date"],
                    }
                    for entry in entries
                ],
                "as_of": as_of.isoformat(),
                "payload": {"cross_checked": len({e.source for e in entries}) >= 2},
            }
        )
    return result
