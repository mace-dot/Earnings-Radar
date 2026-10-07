"""Versioned price features, strictly bounded by the information cutoff."""

from datetime import datetime
from math import log, sqrt
from statistics import stdev
from typing import Any

from engine.providers.base import Observation

VERSION = "price-v1"


def price_features(bars: list[Observation], as_of: datetime) -> dict[str, Any]:
    values = [(item.observed_at, item.at(as_of)) for item in bars]
    values.sort(key=lambda item: item[0])
    closes = [float(value["c"]) for _, value in values]
    output: dict[str, Any] = {
        "version": VERSION,
        "sample_size": len(closes),
        "last_close": closes[-1] if closes else None,
    }
    for horizon in (5, 20, 60):
        output[f"return_{horizon}"] = (
            closes[-1] / closes[-horizon - 1] - 1 if len(closes) > horizon else None
        )
    for horizon in (50, 200):
        output[f"sma_{horizon}_distance"] = (
            closes[-1] / (sum(closes[-horizon:]) / horizon) - 1
            if len(closes) >= horizon
            else None
        )
    returns = (
        [log(b / a) for a, b in zip(closes[-21:-1], closes[-20:])]
        if len(closes) >= 21
        else []
    )
    output["realized_volatility_20"] = (
        stdev(returns) * sqrt(252) if len(returns) >= 20 else None
    )
    true_ranges = []
    for index in range(max(1, len(values) - 14), len(values)):
        bar = values[index][1]
        previous = float(values[index - 1][1]["c"])
        high, low = bar.get("h"), bar.get("l")
        if high is None or low is None:
            continue
        true_ranges.append(
            max(
                float(high) - float(low),
                abs(float(high) - previous),
                abs(float(low) - previous),
            )
        )
    output["atr_14"] = sum(true_ranges) / 14 if len(true_ranges) == 14 else None
    output["adv_20"] = (
        sum(float(v.get("v", 0)) * float(v["c"]) for _, v in values[-20:]) / 20
        if len(values) >= 20 and all(v.get("v") is not None for _, v in values[-20:])
        else None
    )
    output["feed"] = bars[-1].feed if bars else None
    output["as_of"] = as_of.isoformat()
    return output


def implied_move(
    spot: float, call_bid: float, call_ask: float, put_bid: float, put_ask: float
) -> float:
    if (
        spot <= 0
        or min(call_bid, put_bid) < 0
        or call_ask < call_bid
        or put_ask < put_bid
    ):
        raise ValueError("Invalid or crossed straddle quote")
    return ((call_bid + call_ask + put_bid + put_ask) / 2) / spot
