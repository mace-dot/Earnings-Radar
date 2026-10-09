"""Daily Cboe implied-move archive. Earlier days cannot be reconstructed."""

import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from engine.store import Store

BATCH = 25
FEED = "cboe_delayed_implied"
SYMBOL = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def eligible_reports(
    events: list[dict[str, Any]], today: date
) -> list[tuple[str, str]]:
    """Soonest agreed report inside the next 60 days. Disagreements stay out."""
    chosen: dict[str, str] = {}
    horizon = today + timedelta(days=60)
    for event in events:
        symbol = str(event.get("symbol") or "")
        report = str(event.get("report_date") or "")
        try:
            report_day = date.fromisoformat(report)
        except ValueError:
            continue
        if not SYMBOL.fullmatch(symbol) or not today <= report_day <= horizon:
            continue
        dated = {
            source.get("date")
            for source in event.get("sources") or []
            if source.get("source") in {"Finnhub", "Alpha Vantage"}
            and source.get("date")
        }
        if event.get("date_status") == "conflicting" or len(dated) > 1:
            continue
        if symbol not in chosen or report < chosen[symbol]:
            chosen[symbol] = report
    return sorted(chosen.items(), key=lambda item: (item[1], item[0]))


def collect(store: Store, now: datetime, provider: Any = None) -> dict[str, Any]:
    today = now.astimezone(ZoneInfo("America/New_York")).date()
    events = store.pages(
        "earnings_events",
        {
            "select": "symbol,report_date,date_status,sources",
            "and": (
                f"(report_date.gte.{today},report_date.lte.{today + timedelta(days=60)})"
            ),
            "order": "report_date.asc,symbol.asc",
        },
    )
    reports = eligible_reports(events, today)
    saved = set()
    for offset in range(0, len(reports), 80):
        chunk = reports[offset : offset + 80]
        rows = store.read(
            "market_observations",
            {
                "select": "symbol",
                "feed": f"eq.{FEED}",
                "id": "in.("
                + ",".join(f"cboe-implied:{symbol}:{today}" for symbol, _ in chunk)
                + ")",
            },
        )
        saved.update(row["symbol"] for row in rows)
    pending = [(symbol, report) for symbol, report in reports if symbol not in saved]
    if provider is None:
        from engine.providers.public_market import Cboe

        provider = Cboe()
    client = provider
    written = []
    errors = []
    processed = 0
    for symbol, report in pending[:BATCH]:
        processed += 1
        try:
            snapshot = client.event_implied(symbol, report, now)
        except Exception as exc:
            errors.append({"symbol": symbol, "error_type": type(exc).__name__})
            if len(errors) >= 5:
                break
            continue
        if snapshot["observed_at"] > now:
            errors.append({"symbol": symbol, "error_type": "FutureSnapshot"})
            continue
        written.append(
            {
                "id": f"cboe-implied:{symbol}:{today.isoformat()}",
                "symbol": symbol,
                "source": "Cboe",
                "feed": FEED,
                "observed_at": snapshot["observed_at"].isoformat(),
                "retrieved_at": now.isoformat(),
                "payload": snapshot["payload"],
            }
        )
    for offset in range(0, len(written), 50):
        store.write("market_observations", written[offset : offset + 50])
    remaining = max(0, len(pending) - processed)
    return {
        "session_date": today.isoformat(),
        "eligible": len(reports),
        "saved": len(written),
        "remaining": remaining,
        "symbol_errors": errors,
        "continue_today": remaining > 0 and len(errors) < 5,
        "note": "Implied moves start on the day they are saved and are not backfilled",
    }
