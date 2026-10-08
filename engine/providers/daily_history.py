"""Credentialed adjusted daily history, with a single shared market-wide archive."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import exchange_calendars as xcals
import httpx

from engine.providers.base import Observation
from engine.providers.public_market import Nasdaq
from engine.store import ConfigurationError
from engine.history_cache import volume_count

FEED = "massive_daily_adjusted"


def massive_key() -> str:
    return os.getenv("MASSIVE_API_KEY") or os.getenv("POLYGON_API_KEY") or ""


def session_close(session: str) -> datetime:
    year = int(session[:4])
    calendar = xcals.get_calendar(
        "XNYS", start=f"{year-1}-01-01", end=f"{year+1}-12-31"
    )
    return calendar.session_close(session).to_pydatetime()


def recent_sessions(now: datetime, days: int = 120) -> list[str]:
    year = now.year
    calendar = xcals.get_calendar(
        "XNYS", start=f"{year-1}-01-01", end=f"{year+1}-12-31"
    )
    sessions = calendar.sessions_in_range(
        (now - timedelta(days=days)).date().isoformat(), now.date().isoformat()
    )
    return [s.date().isoformat() for s in sessions if calendar.session_close(s) <= now]


class Massive:
    def __init__(self, store: Any) -> None:
        self.store = store
        self.errors: dict[str, str] = {}

    def bars(self, symbols: list[str], start: str, end: str) -> list[Observation]:
        rows = self.store.rpc(
            "radar_history_bars", {"p_symbols": symbols, "p_start": start, "p_end": end}
        )
        observed = {r["symbol"] for r in rows}
        for symbol in symbols:
            if symbol not in observed:
                self.errors[symbol] = "Adjusted history archive not yet available"
        return [
            Observation(
                row["symbol"],
                datetime.fromisoformat(row["observed_at"]),
                datetime.fromisoformat(row["available_at"]),
                row["source"],
                {
                    "t": str(row["session_date"]),
                    "o": row["open"],
                    "h": row["high"],
                    "l": row["low"],
                    "c": row["close"],
                    "v": row["volume"],
                    "adjustment_status": "split-adjusted",
                    "timestamp_kind": "exchange session close, not publication time",
                },
                row["feed"],
            )
            for row in rows
        ]


def history_provider(store: Any, fallback: Any = Nasdaq) -> Any:
    return Massive(store) if massive_key() else fallback()


def collect_day(store: Any, session: str, now: datetime) -> int:
    key = massive_key()
    if not key:
        raise ConfigurationError(
            "MASSIVE_API_KEY missing; a historical-data account is required"
        )
    close = session_close(session)
    if close > now:
        raise ValueError("Forming or future session cannot be archived")
    response = httpx.get(
        f"https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks/{session}",
        params={"adjusted": "true", "include_otc": "false"},
        headers={"Authorization": f"Bearer {key}"},
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("adjusted") is not True or not data.get("results"):
        raise RuntimeError(
            "No verified adjusted daily response; account entitlement or availability must be checked"
        )
    results = []
    for row in data["results"]:
        if (
            not isinstance(row.get("T"), str)
            or not isinstance(row.get("c"), (int, float))
            or row["c"] <= 0
        ):
            continue
        result = {k: row.get(k) for k in ("T", "o", "h", "l", "c")}
        try:
            result["v"] = volume_count(row.get("v"))
        except ValueError:
            result["v"] = None
        results.append(result)
    if not results:
        raise RuntimeError("Daily response has no usable observations")
    acquired = datetime.now(timezone.utc)
    store.write(
        "market_history_days",
        [
            {
                "id": f"{FEED}:{session}",
                "session_date": session,
                "source": "Massive",
                "feed": FEED,
                "observed_at": close.isoformat(),
                "available_at": acquired.isoformat(),
                "payload": {
                    "adjusted": True,
                    "results": results,
                    "usage": "Account-authorized daily aggregates; not streaming or executable quotes",
                },
            }
        ],
        immutable=True,
    )
    return len(results)


def synchronize(store: Any, now: datetime, limit: int = 3) -> dict[str, Any]:
    import time

    if not massive_key():
        raise ConfigurationError(
            "MASSIVE_API_KEY missing; add a historical-data key securely"
        )
    existing = {
        r["session_date"]
        for r in store.pages(
            "market_history_days", {"select": "session_date", "feed": f"eq.{FEED}"}
        )
    }
    wanted = [
        s
        for s in reversed(recent_sessions(now))
        if s not in existing and s < now.date().isoformat()
    ][:limit]
    errors = []
    try:
        split_reference(store, now)
    except Exception as exc:
        errors.append(
            {"provider": "Massive corporate actions", "error_type": type(exc).__name__}
        )
    count = 0
    for index, session in enumerate(wanted):
        if index or wanted:
            # Respect the basic account's five-request/minute budget.
            time.sleep(13)
        count += collect_day(store, session, now)
    return {
        "sessions": wanted,
        "observations": count,
        "feed": FEED,
        "provider_errors": errors,
        "remaining_sessions": len(set(recent_sessions(now)) - existing - set(wanted)),
    }


def split_reference(store: Any, now: datetime) -> bool:
    """Archive a complete reference query before using absence of splits as evidence."""
    sessions = recent_sessions(now)
    end = sessions[-1]
    start = (datetime.fromisoformat(end) - timedelta(days=120)).date().isoformat()
    identity = f"massive_splits_120d:{end}"
    if store.read(
        "market_history_days", {"id": f"eq.{identity}", "select": "id", "limit": "1"}
    ):
        return False
    response = httpx.get(
        "https://api.massive.com/v3/reference/splits",
        params={"execution_date.gte": start, "execution_date.lte": end, "limit": 1000},
        headers={"Authorization": f"Bearer {massive_key()}"},
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "OK" or "next_url" in data:
        raise RuntimeError(
            "Corporate-action reference query is incomplete; validation remains blocked"
        )
    acquired = datetime.now(timezone.utc)
    store.write(
        "market_history_days",
        [
            {
                "id": identity,
                "session_date": end,
                "source": "Massive",
                "feed": "massive_splits_120d",
                "observed_at": acquired.isoformat(),
                "available_at": acquired.isoformat(),
                "payload": {
                    "start": start,
                    "end": end,
                    "complete": True,
                    "results": data.get("results", []),
                },
            }
        ],
        immutable=True,
    )
    return True
