"""Public Nasdaq daily bars and Cboe delayed chains; no access-control bypass."""

from concurrent.futures import ThreadPoolExecutor
import math
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from engine.providers.base import Observation


def number(value: Any) -> float | None:
    try:
        parsed = float(str(value).replace("$", "").replace(",", ""))
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError):
        return None


class Nasdaq:
    def __init__(self) -> None:
        self.errors: dict[str, str] = {}
        self.client = httpx.Client(
            timeout=40,
            headers={"User-Agent": "EarningsRadar/1.0 contact mace@udel.edu"},
        )

    def bars(self, symbols: list[str], start: str, end: str) -> list[Observation]:
        def collect(symbol: str) -> list[Observation]:
            r = self.client.get(
                f"https://api.nasdaq.com/api/quote/{symbol}/historical",
                params={
                    "assetclass": "stocks",
                    "fromdate": start,
                    "todate": end,
                    "limit": 5000,
                },
            )
            if r.status_code in {400, 404}:
                self.errors[symbol] = f"Symbol unavailable (HTTP {r.status_code})"
                return []
            r.raise_for_status()
            data = r.json().get("data") or {}
            if int(data.get("totalRecords") or 0) > 5000:
                raise RuntimeError("Historical pagination exceeds capacity")
            rows = (data.get("tradesTable") or {}).get("rows") or []
            retrieved = datetime.now(timezone.utc)
            output = []
            for row in rows:
                session = datetime.strptime(row["date"], "%m/%d/%Y").date()
                close_time = datetime.combine(
                    session,
                    datetime.min.time().replace(hour=16),
                    ZoneInfo("America/New_York"),
                ).astimezone(timezone.utc)
                close = number(row.get("close"))
                if close_time > retrieved or close is None or close <= 0:
                    continue
                values = {
                    "t": session.isoformat(),
                    "c": close,
                    "o": number(row.get("open")),
                    "h": number(row.get("high")),
                    "l": number(row.get("low")),
                    "v": (
                        int(number(row.get("volume")))
                        if number(row.get("volume")) is not None
                        else None
                    ),
                    "adjustment_status": "unspecified",
                    "timestamp_kind": "conservative session cutoff, not publication time",
                }
                output.append(
                    Observation(
                        symbol,
                        close_time,
                        retrieved,
                        "Nasdaq",
                        values,
                        "nasdaq_daily_adjustment_unspecified",
                    )
                )
            return output

        # Small bounded concurrency; provider denials propagate instead of being bypassed.
        with ThreadPoolExecutor(max_workers=2) as pool:
            return [bar for group in pool.map(collect, symbols) for bar in group]


class Cboe:
    def __init__(self) -> None:
        self.client = httpx.Client(timeout=40, follow_redirects=True)

    def snapshots(self, symbol: str) -> list[Observation]:
        r = self.client.get(
            f"https://cdn.cboe.com/api/global/delayed_quotes/options/{symbol}.json"
        )
        r.raise_for_status()
        data = r.json()
        retrieved = datetime.now(timezone.utc)
        # The feed's UTC snapshot timestamp is distinct from individual quote timestamps.
        stamp = datetime.fromisoformat(data["timestamp"]).replace(tzinfo=timezone.utc)
        if stamp > retrieved:
            raise ValueError("Future option snapshot")
        return [
            Observation(
                symbol,
                stamp,
                retrieved,
                "Cboe",
                {
                    "contract_id": row["option"],
                    "latestQuote": {
                        "bp": row.get("bid"),
                        "ap": row.get("ask"),
                        "t": stamp.isoformat(),
                    },
                    "greeks": {
                        "delta": row.get("delta"),
                        "gamma": row.get("gamma"),
                        "theta": row.get("theta"),
                        "vega": row.get("vega"),
                    },
                    "impliedVolatility": row.get("iv"),
                    "open_interest": row.get("open_interest"),
                    "volume": row.get("volume"),
                    "quote_source": "Cboe delayed snapshot",
                    "quote_timestamp_kind": "snapshot publication; individual quote age unknown",
                    "last_trade_time": row.get("last_trade_time"),
                },
                "cboe_delayed",
            )
            for row in data.get("data", {}).get("options", [])
        ]
