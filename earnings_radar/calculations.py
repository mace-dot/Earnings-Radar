"""
Option cost helpers for Earnings Radar.

These are mechanical quote arithmetic — not calibrated forecasts of the
earnings move, implied move models, or breakout probabilities.
"""

from __future__ import annotations

from typing import Any, Optional


def _num(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mid_price(bid: Optional[float], ask: Optional[float]) -> Optional[float]:
    bid_f, ask_f = _num(bid), _num(ask)
    if bid_f is None or ask_f is None:
        return None
    if bid_f < 0 or ask_f < 0:
        return None
    return (bid_f + ask_f) / 2.0


def spread_pct(bid: Optional[float], ask: Optional[float]) -> Optional[float]:
    """
    Bid/ask spread as a percent of mid: (ask - bid) / mid * 100.
    Returns None when quotes are incomplete or mid is zero.
    """
    bid_f, ask_f = _num(bid), _num(ask)
    mid = mid_price(bid_f, ask_f)
    if bid_f is None or ask_f is None or mid is None or mid == 0:
        return None
    if ask_f < bid_f:
        return None
    return ((ask_f - bid_f) / mid) * 100.0


def straddle_purchase_cost(call_ask: Optional[float], put_ask: Optional[float]) -> Optional[float]:
    """Same-strike call + put purchase cost using ask prices (per share)."""
    c, p = _num(call_ask), _num(put_ask)
    if c is None or p is None:
        return None
    if c < 0 or p < 0:
        return None
    return c + p


def contract_cost(per_share_debit: Optional[float], multiplier: int = 100) -> Optional[float]:
    """Dollar cost for one contract (default 100-share multiplier)."""
    debit = _num(per_share_debit)
    if debit is None:
        return None
    return round(debit * multiplier, 2)


def expiration_breakevens(
    strike: Optional[float],
    call_ask: Optional[float],
    put_ask: Optional[float],
) -> tuple[Optional[float], Optional[float]]:
    """
    Long-straddle expiration breakevens using ask-based purchase cost:
      lower = strike - (call_ask + put_ask)
      upper = strike + (call_ask + put_ask)
    """
    k = _num(strike)
    cost = straddle_purchase_cost(call_ask, put_ask)
    if k is None or cost is None:
        return None, None
    return k - cost, k + cost


def realized_pnl(
    entry_debit: Optional[float],
    exit_credit: Optional[float],
    contracts: int = 1,
    fees: float = 0.0,
    multiplier: int = 100,
) -> Optional[float]:
    """
    Paper P&L for a debit package closed for a credit:
      (exit_credit - entry_debit) * multiplier * contracts - fees
    """
    entry = _num(entry_debit)
    exit_ = _num(exit_credit)
    if entry is None or exit_ is None:
        return None
    n = int(contracts or 1)
    fee = float(fees or 0)
    return round((exit_ - entry) * multiplier * n - fee, 2)


def enrich_quote_row(row: dict[str, Any]) -> dict[str, Any]:
    """Attach derived fields used by the dashboard and exports."""
    out = dict(row)
    out["call_spread_pct"] = spread_pct(row.get("call_bid"), row.get("call_ask"))
    out["put_spread_pct"] = spread_pct(row.get("put_bid"), row.get("put_ask"))
    cost = straddle_purchase_cost(row.get("call_ask"), row.get("put_ask"))
    out["straddle_ask_cost"] = cost
    out["contract_cost"] = contract_cost(cost)
    be_lo, be_hi = expiration_breakevens(
        row.get("strike"), row.get("call_ask"), row.get("put_ask")
    )
    out["breakeven_low"] = be_lo
    out["breakeven_high"] = be_hi
    if cost is not None and _num(row.get("stock_price")):
        sp = float(row["stock_price"])
        out["straddle_cost_pct_of_spot"] = (cost / sp) * 100.0 if sp else None
    else:
        out["straddle_cost_pct_of_spot"] = None
    return out
