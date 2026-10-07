"""Rate-limited historical earnings backfill; dates require session-timing resolution."""

import os
from datetime import datetime, timezone
from typing import Any

import httpx


def alpha_earnings(symbol: str) -> list[dict[str, Any]]:
    key = os.getenv("ALPHAVANTAGE_API_KEY") or os.getenv("ALPHA_VANTAGE_API_KEY")
    if not key:
        raise RuntimeError("Alpha Vantage historical earnings key missing")
    response = httpx.get(
        "https://www.alphavantage.co/query",
        params={"function": "EARNINGS", "symbol": symbol, "apikey": key},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if "quarterlyEarnings" not in data:
        raise RuntimeError("Historical earnings unavailable or rate limited")
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for item in data["quarterlyEarnings"]:
        date = item.get("reportedDate")
        if not date or date == "None":
            continue
        rows.append(
            {
                "id": f"{symbol}:{date}",
                "symbol": symbol,
                "report_date": date,
                "timing": "unknown",
                "date_status": "estimated",
                "sources": [{"source": "Alpha Vantage", "as_of": now}],
                "as_of": now,
                "payload": {
                    "historical": True,
                    "earnings": item,
                    "timing_resolved": False,
                },
            }
        )
    return rows
