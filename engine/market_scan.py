"""Fair, leased full-directory scan with compact auditable observations."""

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from engine.features import price_features
from engine.move_features import setup_features
from engine.providers.base import Observation
from engine.providers.public_market import Nasdaq
from engine.providers.daily_history import history_provider
from engine.store import Store


def scan_payload(observations: list[Observation], cutoff: datetime) -> dict[str, Any]:
    ordered = sorted(observations, key=lambda o: o.observed_at)
    return {
        "features": {
            **price_features(ordered, cutoff),
            **setup_features(ordered, cutoff),
        },
        "observations": [
            {
                "source": o.source,
                "feed": o.feed,
                "observed_at": o.observed_at.isoformat(),
                "available_at": o.available_at.isoformat(),
                "values": o.at(cutoff),
            }
            for o in ordered
        ],
        "classification": "SEC directory identifier; common-share eligibility not verified",
        "scope": "Completed sourced daily sessions; adjustment basis recorded per observation, not streaming",
        "history_policy": "Latest research snapshot, not a point-in-time backtest dataset",
    }


def market_scan(store: Store, limit: int = 100) -> dict[str, Any]:
    claims = store.rpc("radar_claim_market", {"p_limit": limit})
    if not claims:
        return {"claimed": 0, "covered": 0}
    started = datetime.now(timezone.utc)
    error = None
    provider = history_provider(store, Nasdaq)
    try:
        bars = provider.bars(
            [r["symbol"] for r in claims],
            (started - timedelta(days=120)).date().isoformat(),
            started.date().isoformat(),
        )
    except Exception as exc:
        error = (
            f"HTTP {exc.response.status_code}"
            if isinstance(exc, httpx.HTTPStatusError)
            else type(exc).__name__
        )
        bars = []
    cutoff = datetime.now(timezone.utc)
    covered = 0
    failed_count = 0
    feature_rows = []
    for row in claims:
        symbol = row["symbol"]
        symbol_error = error or getattr(provider, "errors", {}).get(symbol)
        observed = [o for o in bars if o.symbol == symbol]
        payload = scan_payload(observed, cutoff)
        failed_symbol = symbol_error and not symbol_error.startswith(
            "Symbol unavailable"
        )
        status = "failed" if failed_symbol else "covered" if observed else "unavailable"
        failed_count += int(status == "failed")
        applied = store.finish_market(
            symbol,
            row["lease_token"],
            {
                "state": status,
                "checked_at": cutoff.isoformat(),
                "next_attempt_at": (
                    cutoff
                    + timedelta(hours=24 if len(observed) >= 60 or not observed else 1)
                ).isoformat(),
                "lease_until": None,
                "lease_token": None,
                "source": observed[0].source if observed else None,
                "feed": observed[0].feed if observed else None,
                "last_session": (
                    max(o.observed_at for o in observed).date().isoformat()
                    if observed
                    else None
                ),
                "sample_size": len(observed),
                "reason": symbol_error
                or (
                    None
                    if observed
                    else "No completed-session bars returned by this feed"
                ),
                "payload": payload,
            },
        )
        if applied and observed:
            feature = payload["features"]
            feature_rows.append(
                {
                    "id": f"{symbol}:market-scan-v1",
                    "symbol": symbol,
                    "version": "market-scan-v1",
                    "as_of": cutoff.isoformat(),
                    "observations": [f"market_coverage:{symbol}"],
                    "values": feature,
                    "missing_reasons": [k for k, v in feature.items() if v is None],
                }
            )
            covered += 1
    store.write("features", feature_rows)
    if error:
        raise RuntimeError(f"Market scan provider failed ({error}); attempts recorded")
    return {
        "claimed": len(claims),
        "covered": covered,
        "unavailable": len(claims) - covered - failed_count,
        "failed": failed_count,
        "scope": "SEC identifiers / completed sourced daily bars",
    }
