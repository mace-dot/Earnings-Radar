"""Alpaca bars and Finnhub calendar. Feed identity is never discarded."""

import os
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from engine.providers.base import Observation


def calendar_chunks(start: str, end: str, days: int = 7) -> list[tuple[str, str]]:
    if days < 1:
        raise ValueError("Calendar chunk must cover at least one day")
    cursor = date.fromisoformat(start)
    last = date.fromisoformat(end)
    if cursor > last:
        return []
    chunks = []
    while cursor <= last:
        chunk_end = min(cursor + timedelta(days=days - 1), last)
        chunks.append((cursor.isoformat(), chunk_end.isoformat()))
        cursor = chunk_end + timedelta(days=1)
    return chunks


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
        output = []
        token = None
        for _ in range(20):
            params: dict[str, Any] = {"feed": "indicative", "limit": 1000}
            if token:
                params["page_token"] = token
            response = self.client.get(
                f"https://data.alpaca.markets/v1beta1/options/snapshots/{symbol}",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            now = datetime.now(timezone.utc)
            output.extend(
                Observation(
                    symbol,
                    now,
                    now,
                    "Alpaca",
                    {"contract_id": contract, **value},
                    "indicative",
                )
                for contract, value in data.get("snapshots", {}).items()
            )
            token = data.get("next_page_token")
            if not token:
                return output
        raise RuntimeError(
            "Option pagination exceeded capacity; partial chain not used"
        )


class Finnhub:
    def __init__(self) -> None:
        key = (
            os.getenv("FINNHUB_API_KEY")
            or os.getenv("FINN_HUB")
            or os.getenv("FINNHUB")
        )
        if not key:
            raise RuntimeError("Finnhub calendar credential missing")
        self.client = httpx.Client(timeout=45, headers={"X-Finnhub-Token": key})

    def calendar(self, start: str, end: str) -> list[Observation]:
        # A wide from/to request comes back as only the far end of the window.
        # Short chunks keep the reports that are actually coming up.
        now = datetime.now(timezone.utc)
        seen: set[tuple[str, str]] = set()
        output = []
        for chunk_start, chunk_end in calendar_chunks(start, end):
            response = self.client.get(
                "https://finnhub.io/api/v1/calendar/earnings",
                params={"from": chunk_start, "to": chunk_end},
            )
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise RuntimeError("Calendar feed unavailable for this account")
            for item in data.get("earningsCalendar", []):
                symbol, report = item.get("symbol"), item.get("date")
                if not symbol or not report or (symbol, report) in seen:
                    continue
                seen.add((symbol, report))
                output.append(Observation(symbol, now, now, "Finnhub", item))
        return output

    def quote(self, symbol: str) -> dict[str, Any]:
        response = self.client.get(
            "https://finnhub.io/api/v1/quote", params={"symbol": symbol}
        )
        response.raise_for_status()
        value = response.json()
        if not value.get("c") or not value.get("t"):
            raise ValueError("No sourced quote available")
        return {
            "p": value["c"],
            "t": datetime.fromtimestamp(value["t"], timezone.utc).isoformat(),
        }
