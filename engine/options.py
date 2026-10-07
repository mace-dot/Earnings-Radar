"""Select purchased contracts using executable, fresh quotes and verified identity."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Contract:
    symbol: str
    kind: str
    strike: float
    expiry: datetime
    bid: float
    ask: float
    delta: float | None
    multiplier: int | None
    observed_at: datetime
    feed: str
    open_interest: int | None = None
    adjusted: bool = False


def select_long(
    contracts: list[Contract], side: str, as_of: datetime
) -> dict[str, Any]:
    if side not in {"BULL", "BEAR"}:
        raise ValueError("Unsupported side")
    desired = "call" if side == "BULL" else "put"
    valid = []
    rejected: dict[str, int] = {}
    for item in contracts:
        reasons = []
        days = (item.expiry.date() - as_of.date()).days
        age = (as_of - item.observed_at).total_seconds()
        if item.kind != desired:
            continue
        if not 14 <= days <= 60:
            reasons.append("expiry_outside_comparison_window")
        if age < 0 or age > 30:
            reasons.append("stale_or_future_quote")
        if item.feed != "opra":
            reasons.append("non_executable_feed")
        if item.multiplier is None or item.multiplier <= 0 or item.adjusted:
            reasons.append("contract_identity_unverified")
        if item.bid <= 0 or item.ask < item.bid:
            reasons.append("crossed_or_unusable_quote")
        mid = (item.bid + item.ask) / 2
        if mid <= 0 or (item.ask - item.bid) / mid > 0.1:
            reasons.append("wide_spread")
        if item.delta is None or not 0.35 <= abs(item.delta) <= 0.65:
            reasons.append("delta_unavailable_or_outside_window")
        if item.open_interest is None or item.open_interest < 250:
            reasons.append("thin_or_unknown_open_interest")
        for reason in reasons:
            rejected[reason] = rejected.get(reason, 0) + 1
        if not reasons:
            valid.append(item)
    if not valid:
        return {
            "contract": None,
            "missing_reasons": rejected or {"matching_contract_missing": 1},
        }
    best = min(
        valid,
        key=lambda c: (
            abs(abs(c.delta or 0) - 0.5),
            (c.ask - c.bid) / ((c.ask + c.bid) / 2),
        ),
    )
    return {
        "contract": best.symbol,
        "premium_basis": "ask",
        "premium": best.ask,
        "one_contract_max_loss": best.ask * int(best.multiplier or 0),
        "as_of": best.observed_at.isoformat(),
        "feed": best.feed,
        "missing_reasons": {},
    }
