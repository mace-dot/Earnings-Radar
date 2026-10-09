"""One weekday pass that spends the remaining free Alpha Vantage calls."""

from datetime import datetime, timezone
from typing import Any

from engine.alpha_budget import plan
from engine.providers.alpha_vantage import AlphaVantage, QuotaExceeded


def _day_start(now: datetime) -> datetime:
    current = now.astimezone(timezone.utc)
    return current.replace(hour=0, minute=0, second=0, microsecond=0)


def collect(store: Any, now: datetime, provider: Any | None = None) -> dict[str, Any]:
    source = provider or AlphaVantage()
    runs_today = store.read(
        "engine_runs",
        {
            "select": "job,as_of,status,payload",
            "as_of": f"gte.{_day_start(now).isoformat()}",
            "order": "as_of.desc",
            "limit": "500",
        },
    )
    history_runs = store.read(
        "engine_runs",
        {
            "select": "job,as_of,status,payload",
            "job": "eq.alpha_scan",
            "order": "as_of.desc",
            "limit": "90",
        },
    )
    events = store.pages(
        "earnings_events",
        {"select": "symbol,report_date", "order": "report_date.asc"},
    )
    securities = store.pages(
        "securities",
        {"select": "symbol,asset_type", "order": "symbol.asc"},
    )
    features = store.pages(
        "latest_price_features",
        {"select": "symbol,values", "order": "symbol.asc"},
    )
    budget = plan(now, runs_today, events, securities, features, history_runs)
    requests: list[dict[str, Any]] = []
    saved = 0
    stopped = None
    for symbol in budget["symbols"]:
        try:
            rows = source.earnings(symbol)
        except QuotaExceeded:
            requests.append(
                {"function": "EARNINGS", "symbol": symbol, "status": "quota"}
            )
            stopped = "quota"
            break
        except Exception as exc:
            requests.append(
                {
                    "function": "EARNINGS",
                    "symbol": symbol,
                    "status": "error",
                    "error_type": type(exc).__name__,
                }
            )
            continue
        if rows:
            for offset in range(0, len(rows), 300):
                store.write("estimate_revisions", rows[offset : offset + 300])
            saved += len(rows)
            reported = [
                row["payload"]["reported_date"]
                for row in rows
                if row["payload"].get("reported_date")
            ]
            requests.append(
                {
                    "function": "EARNINGS",
                    "symbol": symbol,
                    "status": "ok",
                    "quarters": len(rows),
                    "latest_reported": max(reported) if reported else None,
                }
            )
        else:
            requests.append(
                {"function": "EARNINGS", "symbol": symbol, "status": "empty"}
            )
    errors = [row for row in requests if row["status"] in {"error", "quota"}]
    return {
        "alpha_vantage_requests": requests,
        "processed_symbols": len(requests),
        "quarters_saved": saved,
        "planned_symbols": budget["symbols"],
        "used_before": budget["used"],
        "daily_limit": budget["limit"],
        "spare": budget["spare"],
        "budget_day": budget["budget_day"],
        "stopped": stopped,
        "budget_complete": True,
        "provider_errors": errors,
    }
