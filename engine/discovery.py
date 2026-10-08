"""Prioritize measured setups for research, never convert ranks to probabilities."""

from datetime import datetime, timedelta
from typing import Any

from engine.trade_research import research_is_fresh_listing


def select_candidates(
    features: list[dict[str, Any]],
    securities: list[dict[str, Any]],
    researched: dict[str, str],
    as_of: datetime,
    limit: int = 10,
) -> list[dict[str, Any]]:
    identities = {row["symbol"]: row for row in securities}
    candidates = []
    for row in features:
        symbol = row["symbol"]
        identity = identities.get(symbol, {})
        values = row["values"]
        try:
            cutoff = datetime.fromisoformat(row["as_of"])
            if not timedelta(0) <= as_of - cutoff <= timedelta(days=4):
                continue
        except (ValueError, TypeError):
            continue
        if (
            identity.get("asset_type") != "common_stock"
            or not research_is_fresh_listing(
                identity.get("listing_metadata", {}), as_of
            )
            or values.get("sample_size", 0) < 60
            or (values.get("last_close") or 0) < 5
            or (values.get("adv_20") or 0) < 5_000_000
        ):
            continue
        if not research_is_fresh_listing(
            {"retrieved_at": values.get("source_last_observed_at")},
            as_of,
            timedelta(days=4),
        ):
            continue
        # Avoid spending each research slot on the same names within a day.
        prior = researched.get(symbol)
        if prior and as_of - datetime.fromisoformat(prior) < timedelta(hours=20):
            continue
        ratio = values.get("vol_compression_ratio")
        momentum = values.get("return_20")
        candidates.append(
            {
                "symbol": symbol,
                "feature_as_of": row["as_of"],
                "last_researched": prior or "",
                "quiet_ratio": ratio,
                "momentum": momentum,
                "reasons": [
                    *(
                        ["Recent swings are smaller than the 60-session baseline"]
                        if ratio is not None and ratio < 0.8
                        else []
                    ),
                    *(
                        ["The observed 20-session price change exceeds 2%"]
                        if momentum is not None and abs(momentum) >= 0.02
                        else []
                    ),
                    "Liquid common-share research candidate; not a move forecast",
                ],
            }
        )
    selected: list[dict[str, Any]] = []

    def add(rows: list[dict[str, Any]], count: int) -> None:
        seen = {row["symbol"] for row in selected}
        selected.extend(
            row for row in rows if row["symbol"] not in seen and len(selected) < count
        )

    quiet = sorted(
        (
            row
            for row in candidates
            if row["quiet_ratio"] is not None and row["quiet_ratio"] < 0.8
        ),
        key=lambda row: (row["quiet_ratio"], row["last_researched"], row["symbol"]),
    )
    trending = sorted(
        (
            row
            for row in candidates
            if row["momentum"] is not None and abs(row["momentum"]) >= 0.02
        ),
        key=lambda row: (-abs(row["momentum"]), row["last_researched"], row["symbol"]),
    )
    add(quiet, max(1, limit * 2 // 5))
    add(trending, max(1, limit * 4 // 5))
    add(
        sorted(candidates, key=lambda row: (row["last_researched"], row["symbol"])),
        limit,
    )
    return selected
