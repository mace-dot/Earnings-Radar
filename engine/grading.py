"""Direction grading is separate from hypothetical contract profit."""

from datetime import datetime
from typing import Any


def grade_direction(
    pick: dict[str, Any], exit_price: float, graded_at: datetime, source: str
) -> dict[str, Any]:
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
