"""Free-account calendar cross-check. Provider estimates do not confirm an IR date."""

import csv
import io
import os
from datetime import datetime, timezone

import httpx

from engine.providers.base import Observation


class AlphaVantage:
    def calendar(self, start: str, end: str) -> list[Observation]:
        key = os.getenv("ALPHAVANTAGE_API_KEY") or os.getenv("ALPHA_VANTAGE_API_KEY")
        if not key:
            raise RuntimeError("Alpha Vantage free-account key missing")
        response = httpx.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "EARNINGS_CALENDAR",
                "horizon": "3month",
                "apikey": key,
            },
            timeout=45,
        )
        response.raise_for_status()
        if not response.text.startswith("symbol,"):
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
            for row in csv.DictReader(io.StringIO(response.text))
            if start <= row["reportDate"] <= end
        ]
