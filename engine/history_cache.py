"""Reuse auditable collected history without inventing a new observation time."""

from datetime import datetime
from decimal import Decimal
import hashlib
from typing import Any

from engine.providers.base import Observation


def volume_count(value: Any) -> int | None:
    """Accept exact whole-share counts without rounding or fabricating volume."""
    if value is None:
        return None
    number = Decimal(str(value))
    if not number.is_finite() or number < 0 or number != number.to_integral_value():
        raise ValueError("Cached volume must be a finite nonnegative whole count")
    return int(number)


def restore(store: Any, symbols: list[str], cutoff: datetime) -> dict[str, Any]:
    if not symbols:
        return {"bars": 0}
    packs = store.pages(
        "market_coverage",
        {
            "symbol": "in.(" + ",".join(symbols) + ")",
            "state": "eq.covered",
            "select": "symbol,payload",
            "order": "symbol.asc",
        },
    )
    rows = []
    for pack in packs:
        for item in pack["payload"].get("observations", []):
            observation = Observation(
                pack["symbol"],
                datetime.fromisoformat(item["observed_at"]),
                datetime.fromisoformat(item["available_at"]),
                item["source"],
                item["values"],
                item["feed"],
            )
            value = observation.at(cutoff)
            session = value["t"][:10]
            identity = f"{observation.symbol}:{session}:{observation.feed}"
            rows.append(
                {
                    "id": hashlib.sha256(identity.encode()).hexdigest()[:24],
                    "symbol": observation.symbol,
                    "session_date": session,
                    "open": value.get("o"),
                    "high": value.get("h"),
                    "low": value.get("l"),
                    "close": value["c"],
                    "volume": volume_count(value.get("v")),
                    "source": observation.source,
                    "feed": observation.feed,
                    "as_of": observation.observed_at.isoformat(),
                    "available_at": observation.available_at.isoformat(),
                }
            )
    for offset in range(0, len(rows), 400):
        # Existing observations keep their original acquisition metadata.
        store.write("daily_bars", rows[offset : offset + 400], immutable=True)
    return {
        "bars": len(rows),
        "source": "stored coverage observations",
        "timestamps_preserved": True,
    }
