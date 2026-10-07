"""Distinct, source-backed descriptive cases. These are not model contributions."""

from typing import Any


def directional_cases(feature: dict[str, Any]) -> dict[str, list[str]]:
    r20 = feature.get("return_20")
    sma = feature.get("sma_50_distance")
    high = feature.get("dist_52w_high")
    rv = feature.get("rv_10")
    n = feature.get("sample_size", 0)
    bull = [
        (
            f"The 20-session return is {r20:+.1%}; {'upward momentum supports this case' if r20>=0 else 'a bullish case needs a reversal of this decline'}."
            if r20 is not None
            else f"There are {n} daily observations; the 20-session trend is not available."
        ),
        (
            f"The price is {sma:+.1%} from its 50-session average; {'holding above it supports the upward case' if sma>=0 else 'regaining that average would strengthen the upward case'}."
            if sma is not None
            else f"The {n} observations do not establish a 50-session trend."
        ),
        (
            f"The price is {abs(high):.1%} below its 252-session high; a breakout would require buyers to close that gap."
            if high is not None
            else f"A 252-session high comparison is unavailable across {n} observations."
        ),
    ]
    bear = [
        (
            f"The 20-session return is {r20:+.1%}; {'downward momentum supports this case' if r20<0 else 'a bearish case needs evidence that this rise is failing'}."
            if r20 is not None
            else f"Across {n} observations, the downside trend is not established."
        ),
        (
            f"The price is {sma:+.1%} from its 50-session average; {'remaining below it supports the downward case' if sma<0 else 'losing that average would strengthen the downward case'}."
            if sma is not None
            else f"A downside break of the 50-session average cannot be assessed from {n} observations."
        ),
        (
            f"Ten-session realized volatility is {rv:.1%} annualized; this measures past swings, not the chance of a future fall."
            if rv is not None
            else f"There are {n} price observations; the 10-session downside-risk comparison is unavailable."
        ),
    ]
    return {"BULL": bull, "BEAR": bear}


def magnitude_cases(
    feature: dict[str, Any], estimate: dict[str, Any] | None
) -> dict[str, list[str]]:
    implied = (estimate or {}).get("implied_move")
    ratio = feature.get("vol_compression_ratio")
    percentile = feature.get("bb_width_percentile")
    n = feature.get("sample_size", 0)
    more = [
        (
            f"The paired options cost implies a {implied:.1%} move range; MORE studies a reaction beyond that range, before costs."
            if implied is not None
            else "There are 0 usable event-matched option estimates; an implied move comparison is unavailable."
        ),
        (
            f"Short-term versus longer-term realized volatility is {ratio:.2f}×; {'recent prices are quieter' if ratio<1 else 'recent price swings have expanded'}, which is context rather than a breakout forecast."
            if ratio is not None
            else f"The {n} observations do not establish a 10-versus-60-session volatility ratio."
        ),
        (
            f"The current price-band width is at its {percentile:.0%} historical percentile; MORE needs an actual expansion beyond this quietness measure."
            if percentile is not None
            else f"A 60-sample band-width comparison is unavailable across {n} daily observations."
        ),
    ]
    less = [
        (
            f"An estimated {implied:.1%} move is priced into the paired options; LESS studies a reaction inside that range, not a guaranteed option profit."
            if implied is not None
            else "There are 0 event-matched option estimates; LESS cannot be compared with a priced range yet."
        ),
        (
            f"The realized volatility ratio is {ratio:.2f}×; quieter recent trading supports studying a small move but does not rule out a surprise."
            if ratio is not None
            else f"The {n} observations do not prove that recent trading is quieter."
        ),
        (
            f"The price-band percentile is {percentile:.0%}; LESS needs the quiet range to persist despite new information."
            if percentile is not None
            else f"The {n} available observations do not establish how often the current range persists."
        ),
    ]
    return {"MORE": more, "LESS": less}
