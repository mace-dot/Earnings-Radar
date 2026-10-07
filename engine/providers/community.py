"""Authorized public community API. Denials are reported, never bypassed."""

import re
from datetime import datetime, timezone
from typing import Any

import httpx


def stocktwits(symbol: str) -> list[dict[str, Any]]:
    if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}", symbol):
        raise ValueError("Invalid forum symbol")
    response = httpx.get(
        f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json", timeout=20
    )
    response.raise_for_status()
    retrieved = datetime.now(timezone.utc).isoformat()
    rows = []
    for item in response.json().get("messages", []):
        if not isinstance(item.get("id"), int):
            continue
        rows.append(
            {
                "id": f"stocktwits:{item['id']}:{symbol}",
                "symbol": symbol,
                "source": "Stocktwits community opinions",
                "published_at": item["created_at"],
                "retrieved_at": retrieved,
                "payload": {
                    "text": str(item.get("body", ""))[:2000],
                    "url": f"https://stocktwits.com/message/{item['id']}",
                    "sentiment": item.get("entities", {}).get("sentiment"),
                    "coverage": "bounded_recent_sample",
                },
            }
        )
    return rows
