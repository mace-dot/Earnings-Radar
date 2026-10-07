"""Alpaca bars and Finnhub calendar. Feed identity is never discarded."""

import os
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from engine.providers.base import Observation


def stamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class Alpaca:
    def __init__(self) -> None:
        self.client = httpx.Client(
            timeout=45,
            headers={
                "APCA-API-KEY-ID": os.environ.get("ALPACA_API_KEY", ""),
                "APCA-API-SECRET-KEY": os.environ.get("ALPACA_API_SECRET", ""),
            },
        )

    def bars(self, symbols: list[str], start: str, end: str) -> list[Observation]:
        output = []
        token = None
        for _ in range(100):
            params: dict[str, Any] = {
                "symbols": ",".join(symbols),
                "start": start,
                "end": end,
                "timeframe": "1Day",
                "feed": "iex",
                "adjustment": "split",
                "limit": 10000,
            }
            if token:
                params["page_token"] = token
            response = self.client.get(
                "https://data.alpaca.markets/v2/stocks/bars", params=params
            )
            response.raise_for_status()
            data = response.json()
            retrieved = datetime.now(timezone.utc)
            for symbol, bars in data.get("bars", {}).items():
                for bar in bars:
                    if float(bar["c"]) <= 0:
                        raise ValueError("Invalid closing price")
                    # Historical rows retrieved today are not proof of historical availability.
                    session_close = datetime.combine(
                        stamp(bar["t"]).date(),
                        datetime.min.time().replace(hour=16),
                        ZoneInfo("America/New_York"),
                    ).astimezone(timezone.utc)
                    if session_close > retrieved:
                        # A still-forming daily bar is not a completed session close.
                        continue
                    output.append(
                        Observation(
                            symbol,
                            session_close,
                            retrieved,
                            "Alpaca",
                            dict(bar),
                            "iex_split_adjusted",
                        )
                    )
            token = data.get("next_page_token")
            if not token:
                return output
        raise RuntimeError("Price pagination exceeded bounded capacity")

    def snapshots(self, symbol: str) -> list[Observation]:
        response = self.client.get(
            f"https://data.alpaca.markets/v1beta1/options/snapshots/{symbol}",
            params={"feed": "indicative", "limit": 1000},
        )
        response.raise_for_status()
        now = datetime.now(timezone.utc)
        return [
            Observation(
                symbol,
                now,
                now,
                "Alpaca",
                {"contract_id": contract, **value},
                "indicative",
            )
            for contract, value in response.json().get("snapshots", {}).items()
        ]


class Finnhub:
    def __init__(self) -> None:
        key = (
            os.getenv("FINNHUB_API_KEY")
            or os.getenv("FINNHUB")
            or os.getenv("FINN_HUB")
        )
        if not key:
            raise RuntimeError("Finnhub calendar credential missing")
        self.client = httpx.Client(timeout=45, headers={"X-Finnhub-Token": key})

    def calendar(self, start: str, end: str) -> list[Observation]:
        response = self.client.get(
            "https://finnhub.io/api/v1/calendar/earnings",
            params={"from": start, "to": end},
        )
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError("Calendar feed unavailable for this account")
        now = datetime.now(timezone.utc)
        return [
            Observation(item["symbol"], now, now, "Finnhub", item)
            for item in data.get("earningsCalendar", [])
            if item.get("symbol") and item.get("date")
        ]
