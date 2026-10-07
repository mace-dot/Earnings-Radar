"""Direction grading is separate from hypothetical contract profit."""

from datetime import datetime
from typing import Any


def grade_direction(
    pick: dict[str, Any], exit_price: float, graded_at: datetime, source: str
) -> dict[str, Any]:
    if pick["side"] not in {"BULL", "BEAR"}:
        raise ValueError("Magnitude props require magnitude grading")
    entry = pick["payload"].get("entry")
    if not entry or exit_price <= 0:
        raise ValueError("Verified entry and exit prices required")
    if graded_at < datetime.fromisoformat(pick["expires_at"].replace("Z", "+00:00")):
        raise ValueError("Pick has not reached its evaluation horizon")
    price_return = exit_price / entry - 1
    directional = price_return if pick["side"] == "BULL" else -price_return
    return {
        "id": f"{pick['id']}:outcome",
        "pick_id": pick["id"],
        "graded_at": graded_at.isoformat(),
        "source": source,
        "payload": {
            "return_fraction": directional,
            "result": (
                "win" if directional > 0 else "loss" if directional < 0 else "flat"
            ),
            "exit_price": exit_price,
            "metric": "directional_underlying_return",
            "contract_pnl": None,
        },
    }


def grade_magnitude(
    pick: dict[str, Any], exit_price: float, graded_at: datetime, source: str
) -> dict[str, Any]:
    if pick["side"] not in {"MORE", "LESS"}:
        raise ValueError("Magnitude side required")
    entry = pick["payload"].get("entry")
    threshold = pick["payload"].get("implied_move")
    if not entry or not threshold or exit_price <= 0:
        raise ValueError("Verified entry and published magnitude threshold required")
    if graded_at < datetime.fromisoformat(pick["expires_at"].replace("Z", "+00:00")):
        raise ValueError("Pick has not reached its evaluation horizon")
    actual = abs(exit_price / entry - 1)
    hit = actual > threshold if pick["side"] == "MORE" else actual < threshold
    return {
        "id": f"{pick['id']}:outcome",
        "pick_id": pick["id"],
        "graded_at": graded_at.isoformat(),
        "source": source,
        "payload": {
            "result": "flat" if actual == threshold else "win" if hit else "loss",
            "actual_move": actual,
            "published_threshold": threshold,
            "metric": "underlying_magnitude",
            "contract_pnl": None,
        },
    }
