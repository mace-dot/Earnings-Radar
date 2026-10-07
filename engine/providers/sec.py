"""Official SEC identifiers and filings; directory membership is not liquidity."""

import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx

DIRECTORY = "https://www.sec.gov/files/company_tickers_exchange.json"


class SEC:
    def __init__(self) -> None:
        self.client = httpx.Client(
            timeout=45,
            headers={
                "User-Agent": os.getenv("SEC_USER_AGENT", "EarningsRadar mace@udel.edu")
            },
        )

    def securities(self) -> list[dict[str, Any]]:
        response = self.client.get(DIRECTORY)
        response.raise_for_status()
        data = response.json()
        now = datetime.now(timezone.utc).isoformat()
        rows = []
        for values in data["data"]:
            item = dict(zip(data["fields"], values, strict=True))
            symbol = item["ticker"]
            if not re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,14}", symbol):
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "cik": str(item["cik"]).zfill(10),
                    "name": item["name"],
                    "exchange": item["exchange"],
                    "active": True,
                    "asset_type": "unverified",
                    "sector": "Unclassified",
                    "source": DIRECTORY,
                    "as_of": now,
                }
            )
        if len(rows) < 1000:
            raise ValueError(
                "Unexpectedly small SEC directory; preserve existing cache"
            )
        return rows

    def fundamentals(self, cik: str) -> dict[str, Any]:
        if not re.fullmatch(r"\d{10}", cik):
            raise ValueError("Invalid CIK")
        response = self.client.get(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        )
        response.raise_for_status()
        return response.json()
