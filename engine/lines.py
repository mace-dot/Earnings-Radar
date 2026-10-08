"""Explain both cases without inventing a validated probability or option quote."""

from datetime import datetime, timedelta
from typing import Any
from engine.evidence import directional_cases, magnitude_cases, business_cases

KINDS = ("Run-Up", "Earnings Move", "Direction", "IV Ramp", "Drift", "Swing")


def build_lines(
    symbol: str,
    feature: dict[str, Any],
    as_of: datetime,
    event: dict[str, Any] | None = None,
    option_estimate: dict[str, Any] | None = None,
    financial_context: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    lines, sides = [], []
    momentum = feature.get("return_20")
    last = feature.get("last_close")
    atr = feature.get("atr_14")
    for kind in KINDS:
        magnitude = kind in {"Earnings Move", "IV Ramp"}
        cases = (
            magnitude_cases(feature, option_estimate)
            if magnitude
            else directional_cases(feature)
        )
        if not magnitude:
            financial_cases = business_cases(financial_context, as_of)
            for direction in ("BULL", "BEAR"):
                cases[direction].extend(financial_cases[direction])
        missing = []
        if kind != "Swing" and not event:
            missing.append("Earnings date missing")
        if kind in ("Earnings Move", "IV Ramp", "Direction"):
            missing.append("Executable option quotes missing")
        if kind == "Drift":
            missing.append("Verified earnings surprise missing")
        if kind == "Run-Up":
            missing.append("Event-history sample missing")
        if momentum is None:
            missing.append("Price history missing")
        if event and event["date_status"] != "confirmed":
            missing.append(
                "Estimated date"
                if event["date_status"] == "estimated"
                else "Conflicting dates"
            )
        badges = [*missing, "Model not validated"]
        if (feature.get("feed") or "").startswith("iex"):
            badges.append("Partial market feed")
        if "adjustment_unspecified" in (feature.get("feed") or ""):
            badges.append("Historical corporate-action adjustment basis unverified")
        report = event["report_date"] if event else "date unconfirmed"
        line_id = f"{symbol}:{kind}:{as_of.date().isoformat()}"
        favored = (
            "BULL"
            if momentum is not None and momentum > 0
            else "BEAR" if momentum is not None and momentum < 0 else None
        )
        # Momentum informs Swing only; do not claim event/volatility models exist.
        if kind != "Swing":
            favored = None
        lines.append(
            {
                "id": line_id,
                "symbol": symbol,
                "event_id": event["id"] if event else None,
                "kind": kind,
                "as_of": as_of.isoformat(),
                "expires_at": (as_of + timedelta(days=1)).isoformat(),
                "source": "rules-v1",
                "payload": {
                    "subtitle": (
                        "MORE: larger move · LESS: smaller move"
                        if magnitude
                        else f"Report: {report}"
                    ),
                    "favored": favored,
                    "badges": badges,
                },
            }
        )
        for side in (("MORE", "LESS") if magnitude else ("BULL", "BEAR")):
            upward = side == "BULL"
            stop = (
                round(last - 1.5 * atr, 2)
                if last is not None and atr is not None and upward
                else None
            )
            if stop is not None and stop <= 0:
                stop = None
            trade_missing = []
            if not last or not atr:
                trade_missing.append("Entry and stop need recent price history")
            if not upward:
                trade_missing.append(
                    "A purchased put requires an executable contract quote"
                )
            if kind != "Swing":
                trade_missing.extend(missing)
            trade = {
                "instrument": "Shares with stop" if upward else "Long put research",
                "explanation": (
                    "Price context for a share setup. Stops may fill below the stop during a gap; shares can lose their full value."
                    if upward
                    else "Buying a put limits the loss to its premium. No contract or premium is invented."
                ),
                "entry": last if upward else None,
                "stop": stop,
                "max_loss": last if upward else None,
                "exit": (
                    "Review within 60 trading sessions or when the case breaks"
                    if kind == "Swing"
                    else "Event-specific exit needs a verified date and strategy inputs"
                ),
                "missing": list(dict.fromkeys(trade_missing)),
            }
            bullets = cases[side]
            opposite = {"BULL": "BEAR", "BEAR": "BULL", "MORE": "LESS", "LESS": "MORE"}[
                side
            ]
            if magnitude:
                trade = {
                    "instrument": (
                        "Long straddle estimate"
                        if side == "MORE"
                        else "Defined-risk condor research (advanced)"
                    ),
                    "explanation": (
                        "Indicative paired-option cost, not an executable offer. Verify the contract deliverable and current spread before any trade."
                        if side == "MORE"
                        else "Selling volatility requires a complete four-leg defined-risk structure. No naked option sale is suggested."
                    ),
                    "entry": None,
                    "stop": None,
                    "max_loss": (
                        (option_estimate or {}).get(
                            "estimated_one_standard_contract_cost"
                        )
                        if side == "MORE"
                        else None
                    ),
                    "exit": "Exit timing requires a verified event date and strategy inputs",
                    "missing": (
                        ["Indicative only; deliverable unverified"]
                        if option_estimate and side == "MORE"
                        else ["Complete event-matched structure unavailable"]
                    ),
                    "estimate": option_estimate if side == "MORE" else None,
                }
            sides.append(
                {
                    "id": f"{line_id}:{side}",
                    "line_id": line_id,
                    "side": side,
                    "as_of": as_of.isoformat(),
                    "payload": {
                        "tier": "Lean",
                        "sample_size": 0,
                        "probability": None,
                        "score": (
                            abs(momentum)
                            if favored == side and momentum is not None
                            else 0
                        ),
                        "bullets": bullets,
                        "countercase": cases[opposite][:2] + cases[opposite][3:],
                        "financial_context": financial_context,
                        "invalidation": "Review when the price direction reverses, a new filing changes the case, or the event date changes.",
                        "trade": trade,
                        "badges": badges,
                    },
                }
            )
    return lines, sides


def exposure(
    premium: float,
    multiplier: int,
    account_budget: float | None = None,
    risk_fraction: float = 0.01,
) -> dict[str, Any]:
    if premium <= 0 or multiplier <= 0:
        raise ValueError("Positive premium and verified multiplier required")
    cost = premium * multiplier
    if account_budget is None:
        return {
            "one_contract_loss": cost,
            "quantity": None,
            "reason": "Account budget not provided",
        }
    if account_budget <= 0 or not 0 < risk_fraction <= 0.02:
        raise ValueError("Invalid approved budget")
    return {
        "one_contract_loss": cost,
        "quantity": int(account_budget * risk_fraction // cost),
    }
