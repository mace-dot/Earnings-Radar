"""Observed setup measures are not calibrated move probabilities."""

from datetime import datetime
from math import log, sqrt
from statistics import mean, median, stdev
from typing import Any

from engine.providers.base import Observation


def realized(closes: list[float], window: int) -> float | None:
    if len(closes) < window + 1:
        return None
    tail = closes[-window - 1 :]
    return stdev(log(b / a) for a, b in zip(tail, tail[1:])) * sqrt(252)


def setup_features(bars: list[Observation], as_of: datetime) -> dict[str, Any]:
    ordered = sorted(bars, key=lambda b: b.observed_at)
    closes = [float(b.at(as_of)["c"]) for b in ordered]
    rv10, rv60 = realized(closes, 10), realized(closes, 60)
    widths = []
    for end in range(20, len(closes) + 1):
        values = closes[end - 20 : end]
        widths.append(4 * stdev(values) / mean(values))
    trailing = widths[-252:]
    return {
        "rv_10": rv10,
        "rv_60": rv60,
        "vol_compression_ratio": rv10 / rv60 if rv10 is not None and rv60 else None,
        "bb_width_percentile": (
            sum(w <= trailing[-1] for w in trailing) / len(trailing)
            if len(trailing) >= 60
            else None
        ),
        "dist_52w_high": (
            closes[-1] / max(closes[-252:]) - 1 if len(closes) >= 252 else None
        ),
        "move_probability": None,
        "move_meter": None,
        "model_edge": "Not yet evaluated",
        "setup_observations": len(closes),
    }


def event_volatility(iv1: float, t1: float, iv2: float, t2: float) -> float:
    if not 0 < t1 < t2 or min(iv1, iv2) <= 0:
        raise ValueError("Two positive IVs and ordered post-event maturities required")
    base_variance = (iv2 * iv2 * t2 - iv1 * iv1 * t1) / (t2 - t1)
    event_variance = (iv1 * iv1 - base_variance) * t1
    if base_variance < 0 or event_variance < 0:
        raise ValueError(
            "Term structure does not support this event-variance decomposition"
        )
    return sqrt(event_variance)


def historical_moves(
    events: list[dict[str, Any]], closes: dict[str, float]
) -> dict[str, Any]:
    # Event session mapping must be resolved using an exchange calendar before calling.
    moves = []
    for event in events:
        before = closes.get(event["before_session"])
        after = closes.get(event["after_session"])
        if before and after:
            moves.append(abs(after / before - 1))
    tail = moves[-12:]
    return {
        "historical_event_n": len(tail),
        "hist_abs_move_mean": mean(tail) if tail else None,
        "hist_abs_move_median": median(tail) if tail else None,
        "hist_abs_move_max": max(tail) if tail else None,
    }
