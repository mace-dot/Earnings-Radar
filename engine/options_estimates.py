"""Indicative comparison estimates, strictly separate from executable contracts."""

import re
from datetime import date, datetime
from typing import Any

from engine.features import implied_move


def parse_contract(symbol: str, contract: str) -> dict[str, Any] | None:
    match = re.fullmatch(re.escape(symbol) + r"(\d{6})([CP])(\d{8})", contract)
    if not match:
        return None
    try:
        expiry = datetime.strptime(match[1], "%y%m%d").date()
    except ValueError:
        return None
    return {
        "contract": contract,
        "expiry": expiry.isoformat(),
        "kind": "call" if match[2] == "C" else "put",
        "strike": int(match[3]) / 1000,
    }


def chain_estimate(
    symbol: str,
    spot: float,
    snapshots: list[dict[str, Any]],
    as_of: datetime,
    report_date: str | None = None,
) -> dict[str, Any]:
    parsed = []
    cutoff = date.fromisoformat(report_date) if report_date else as_of.date()
    for item in snapshots:
        contract = parse_contract(symbol, item["contract_id"])
        quote = item.get("latestQuote") or {}
        bid, ask = quote.get("bp"), quote.get("ap")
        if not contract or bid is None or ask is None or bid <= 0 or ask < bid:
            continue
        mid = (bid + ask) / 2
        if (ask - bid) / mid > 0.25 or date.fromisoformat(contract["expiry"]) <= cutoff:
            continue
        parsed.append(
            {
                **contract,
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "quote_as_of": quote.get("t"),
                "iv": item.get("impliedVolatility"),
                "greeks": item.get("greeks"),
                "wide_spread": (ask - bid) / mid > 0.1,
            }
        )
    pairs = []
    for call in (c for c in parsed if c["kind"] == "call"):
        put = next(
            (
                p
                for p in parsed
                if p["kind"] == "put"
                and p["strike"] == call["strike"]
                and p["expiry"] == call["expiry"]
            ),
            None,
        )
        if put:
            pairs.append((call, put))
    if not pairs:
        return {
            "implied_move": None,
            "reason": "No usable paired option quotes",
            "quote_kind": "Indicative estimate",
        }
    call, put = min(
        pairs, key=lambda pair: (pair[0]["expiry"], abs(pair[0]["strike"] - spot))
    )
    quote_times = []
    for leg in (call, put):
        if leg["quote_as_of"]:
            stamp = datetime.fromisoformat(leg["quote_as_of"].replace("Z", "+00:00"))
            if stamp > as_of:
                raise ValueError("Quote unavailable at cutoff")
            quote_times.append(stamp)
    quoted_at = min(quote_times).isoformat() if len(quote_times) == 2 else None
    fraction = implied_move(spot, call["bid"], call["ask"], put["bid"], put["ask"])
    return {
        "implied_move": fraction,
        "event_specific": report_date is not None,
        "expiry": call["expiry"],
        "strike": call["strike"],
        "call": call,
        "put": put,
        "debit_per_share": call["mid"] + put["mid"],
        "estimated_one_standard_contract_cost": 100 * (call["mid"] + put["mid"]),
        "multiplier_assumption": "100 shares; deliverable unverified",
        "quote_kind": "Indicative estimate",
        "source": "Alpaca indicative",
        "as_of": quoted_at,
        "retrieved_at": as_of.isoformat(),
        "executable": False,
        "lower_breakeven": call["strike"] - call["mid"] - put["mid"],
        "upper_breakeven": call["strike"] + call["mid"] + put["mid"],
    }
