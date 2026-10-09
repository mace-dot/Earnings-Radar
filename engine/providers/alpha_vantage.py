"""Free-account earnings calendar and reported-history calls."""

import csv
import io
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from engine.providers.base import Observation

SYMBOL = re.compile(r"[A-Z0-9][A-Z0-9.-]{0,14}")


class QuotaExceeded(RuntimeError):
    """The free daily allowance rejected another call. The body is not retained."""


def _key() -> str:
    key = os.getenv("ALPHAVANTAGE_API_KEY") or os.getenv("ALPHA_VANTAGE_API_KEY")
    if not key:
        raise RuntimeError("Alpha Vantage free-account key missing")
    return key


def _reject_quota(payload: dict[str, Any]) -> None:
    message = " ".join(
        str(payload.get(name, "")) for name in ("Note", "Information", "Error Message")
    ).lower()
    if any(
        phrase in message
        for phrase in (
            "call frequency",
            "api call volume",
            "higher api call",
            "spreading out",
            "thank you for using alpha vantage",
            "premium",
        )
    ):
        raise QuotaExceeded("Alpha Vantage request limit reached")


def _optional_number(value: Any) -> float | None:
    if value is None or value in {"", "None"}:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def normalize_earnings(
    symbol: str, payload: dict[str, Any], retrieved: datetime
) -> list[dict[str, Any]]:
    if not SYMBOL.fullmatch(symbol):
        raise ValueError("Invalid earnings symbol")
    _reject_quota(payload)
    rows = []
    for item in payload.get("quarterlyEarnings") or []:
        fiscal = item.get("fiscalDateEnding")
        reported = item.get("reportedDate")
        if not fiscal or not reported:
            continue
        rows.append(
            {
                "id": f"av:{symbol}:{fiscal}",
                "symbol": symbol,
                "period": fiscal,
                "source": "Alpha Vantage",
                "as_of": retrieved.isoformat(),
                "payload": {
                    "reported_date": reported,
                    "reported_eps": _optional_number(item.get("reportedEPS")),
                    "estimated_eps": _optional_number(item.get("estimatedEPS")),
                    "surprise": _optional_number(item.get("surprise")),
                    "surprise_percentage": _optional_number(
                        item.get("surprisePercentage")
                    ),
                    "availability": "First saved at retrieval. The feed did not provide the original estimate publication time.",
                },
            }
        )
    return rows


class AlphaVantage:
    def calendar(self, start: str, end: str) -> list[Observation]:
        response = httpx.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "EARNINGS_CALENDAR",
                "horizon": "3month",
                "apikey": _key(),
            },
            timeout=45,
        )
        response.raise_for_status()
        text = response.text
        if not text.startswith("symbol,"):
            try:
                _reject_quota(json.loads(text))
            except json.JSONDecodeError:
                pass
            raise RuntimeError("Calendar quota or entitlement unavailable")
        now = datetime.now(timezone.utc)
        return [
            Observation(
                row["symbol"],
                now,
                now,
                "Alpha Vantage",
                {**row, "date": row["reportDate"]},
            )
            for row in csv.DictReader(io.StringIO(text))
            if SYMBOL.fullmatch(row.get("symbol", ""))
            and start <= row.get("reportDate", "") <= end
        ]

    def earnings(self, symbol: str) -> list[dict[str, Any]]:
        if not SYMBOL.fullmatch(symbol):
            raise ValueError("Invalid earnings symbol")
        response = httpx.get(
            "https://www.alphavantage.co/query",
            params={"function": "EARNINGS", "symbol": symbol, "apikey": _key()},
            timeout=45,
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Alpha Vantage earnings response was not usable"
            ) from exc
        return normalize_earnings(symbol, payload, datetime.now(timezone.utc))
