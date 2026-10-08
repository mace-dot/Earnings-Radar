"""Deterministic, unvalidated paper research; never an executable recommendation."""

import math
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from engine.options_estimates import parse_contract

VERSION = "paper-momentum-options-v2-public-feeds"
SUPPORTED_VERSIONS = ("paper-momentum-options-v1", VERSION)


def research_is_fresh(payload: dict[str, Any], as_of: datetime) -> bool:
    """Quote refresh cannot renew the age of an independently collected chain."""
    try:
        collected = datetime.fromisoformat(payload["research_retrieved_at"])
        return timedelta(0) <= as_of - collected < timedelta(hours=1)
    except (KeyError, TypeError, ValueError):
        return False


def long_options(
    symbol: str, spot: float, snapshots: list[dict[str, Any]], as_of: datetime
) -> dict[str, dict[str, Any]]:
    if not math.isfinite(spot) or spot <= 0:
        raise ValueError("Positive finite underlying reference required")
    candidates: dict[str, list[dict[str, Any]]] = {"BULL": [], "BEAR": []}
    for item in snapshots:
        contract = parse_contract(symbol, item.get("contract_id", ""))
        if not contract:
            continue
        expiry = datetime.fromisoformat(contract["expiry"]).date()
        dte = (expiry - as_of.date()).days
        q = item.get("latestQuote") or {}
        bid, ask = q.get("bp"), q.get("ap")
        delta = (item.get("greeks") or {}).get("delta")
        if not all(
            isinstance(v, (int, float)) and math.isfinite(v) for v in (bid, ask, delta)
        ):
            continue
        if not 14 <= dte <= 60 or not 0 < bid <= ask or not 0.35 <= abs(delta) <= 0.65:
            continue
        if (contract["kind"] == "call") != (delta > 0):
            continue
        if (ask - bid) / ((ask + bid) / 2) > 0.25 or not q.get("t"):
            continue
        quoted = datetime.fromisoformat(q["t"].replace("Z", "+00:00"))
        age = (as_of - quoted).total_seconds()
        if not 0 <= age <= timedelta(days=4).total_seconds():
            continue
        side = "BULL" if contract["kind"] == "call" else "BEAR"
        candidates[side].append(
            {
                **contract,
                "bid": bid,
                "ask": ask,
                "delta": delta,
                "quote_as_of": quoted.isoformat(),
                "quote_age_seconds": age,
                "dte": dte,
                "source": item.get("quote_source", "Retained historical option source"),
                "timestamp_kind": item.get(
                    "quote_timestamp_kind", "provider quote timestamp"
                ),
            }
        )
    result = {}
    for side, rows in candidates.items():
        if not rows:
            continue
        chosen = min(
            rows,
            key=lambda r: (
                abs(r["dte"] - 30),
                abs(abs(r["delta"]) - 0.5),
                r["ask"] - r["bid"],
            ),
        )
        cost = chosen["ask"] * 100
        result[side] = {
            "instrument": (
                "Long call research" if side == "BULL" else "Long put research"
            ),
            "explanation": "An automatically selected purchased option, using the quoted ask as a paper cost reference. This indicative quote is not an executable offer or an assumed fill.",
            "entry": None,
            "stop": None,
            "max_loss": cost,
            "exit": f"Paper evaluation at expiration ({chosen['expiry']}); review sooner if the trend reverses. A real earlier sale needs a new quote.",
            "missing": [
                chosen["source"],
                chosen["timestamp_kind"],
                "100-share standard deliverable assumed, not verified",
                "Model unvalidated",
                (
                    "Delayed snapshot research, not live entry"
                    if chosen["quote_age_seconds"] > 30
                    else "Current executable quote required"
                ),
            ],
            "contract": {
                **chosen,
                "premium_reference": "ask",
                "cost": cost,
                "multiplier": 100,
                "deliverable_verified": False,
                "breakeven": (
                    chosen["strike"] + chosen["ask"]
                    if side == "BULL"
                    else chosen["strike"] - chosen["ask"]
                ),
                "spot_reference": spot,
                "source": chosen["source"],
                "executable": False,
            },
        }
    return result


def paper_pick(
    line: dict[str, Any],
    side: dict[str, Any],
    feature: dict[str, Any],
    observation_ids: list[str],
    as_of: datetime,
) -> dict[str, Any] | None:
    trade = side["payload"]["trade"]
    contract = trade.get("contract")
    momentum, distance = feature.get("return_20"), feature.get("sma_50_distance")
    if line["kind"] != "Swing" or not contract or momentum is None or distance is None:
        return None
    favored = "BULL" if momentum > 0 else "BEAR"
    if side["side"] != favored or momentum * distance <= 0 or abs(momentum) < 0.02:
        return None
    if (
        feature.get("sample_size", 0) < 60
        or (feature.get("adv_20") or 0) < 5_000_000
        or (feature.get("last_close") or 0) < 5
    ):
        return None
    expiry = datetime.combine(
        datetime.fromisoformat(contract["expiry"]).date(),
        time(16),
        ZoneInfo("America/New_York"),
    )
    return {
        "id": f"{line['id']}:{favored}:{VERSION}",
        "line_id": line["id"],
        "symbol": line["symbol"],
        "side": favored,
        "as_of": as_of.isoformat(),
        "expires_at": expiry.isoformat(),
        "strategy_version": VERSION,
        "observations": observation_ids,
        "payload": {
            "line_kind": "Swing",
            "tier": "Lean",
            "probability": None,
            "status": "UNVALIDATED_PAPER_RESEARCH",
            "entry": contract["spot_reference"],
            "trade": trade,
            "bullets": side["payload"]["bullets"],
            "countercase": side["payload"]["countercase"],
            "financial_context": side["payload"].get("financial_context"),
            "invalidation": "The 20-session trend and 50-session moving-average direction disagree, or new company news changes the case.",
            "selection_rule": "At least 60 bars, price >= $5, source-observed average daily dollar volume >= $5m, absolute 20-session return >= 2%, and trend agrees with the 50-session average. Compare 14–60-day contracts with absolute delta 0.35–0.65; prefer 30 days and delta 0.5.",
            "grading_rule": "Expiration-session underlying direction and hypothetical intrinsic payoff minus the recorded ask cost. No actual fill or pre-expiry option P&L is implied.",
            "feature_as_of": feature.get("as_of"),
            "source": contract["source"],
        },
    }


def expiration_outcome(
    pick: dict[str, Any], bar: dict[str, Any], as_of: datetime
) -> dict[str, Any]:
    contract = pick["payload"]["trade"]["contract"]
    expiry = datetime.fromisoformat(pick["expires_at"])
    if as_of < expiry or bar["session_date"] != contract["expiry"]:
        raise ValueError(
            "Exact expiration-session close required after the evaluation horizon"
        )
    if not math.isfinite(float(bar["close"])) or float(bar["close"]) <= 0:
        raise ValueError("Positive finite expiration close required")
    for field in ("as_of", "available_at"):
        if datetime.fromisoformat(bar[field].replace("Z", "+00:00")) > as_of:
            raise ValueError("Future grading observation")
    from engine.grading import grade_direction

    outcome = grade_direction(
        pick, float(bar["close"]), as_of, f"{bar['source']} {bar['feed']}"
    )
    intrinsic = max(
        0,
        (
            float(bar["close"]) - contract["strike"]
            if contract["kind"] == "call"
            else contract["strike"] - float(bar["close"])
        ),
    )
    pnl = intrinsic * contract["multiplier"] - contract["cost"]
    outcome["payload"].update(
        {
            "result": "win" if pnl > 0 else "loss" if pnl < 0 else "flat",
            "direction_result": outcome["payload"]["result"],
            "metric": "hypothetical_expiration_payoff",
            "hypothetical_pnl": pnl,
            "hypothetical_return": pnl / contract["cost"],
            "contract_pnl": None,
            "fill_assumed": False,
            "fees_included": False,
            "deliverable_verified": False,
            "exit_observation_id": bar["id"],
            "note": "Paper ask reference and assumed 100-share deliverable; not executed P&L. The source closing price is a proxy, not official option settlement; adjustments require separate verification.",
        }
    )
    return outcome
