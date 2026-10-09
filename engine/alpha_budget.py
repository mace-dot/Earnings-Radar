"""Spend the 25-call Alpha Vantage day on upcoming earnings, not on prices or news."""

from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

LIMIT = 25
SPARE = 1
LOOKAHEAD = 60
RECENT_REPORT = 5
SOON = 14


def budget_day(now: datetime) -> str:
    """UTC date. The provider does not publish its reset clock; a limit response still stops the run."""
    return now.astimezone(timezone.utc).date().isoformat()


def _items(run: dict[str, Any]) -> list[dict[str, Any]]:
    payload = run.get("payload") or {}
    listed = payload.get("alpha_vantage_requests")
    if isinstance(listed, list):
        return [item for item in listed if isinstance(item, dict)]
    if (
        run.get("job") == "calendar"
        and run.get("status") in {"completed", "partial"}
        and payload.get("events")
        and not any(
            error.get("provider") == "AlphaVantage"
            for error in payload.get("provider_errors") or []
            if isinstance(error, dict)
        )
    ):
        return [{"function": "EARNINGS_CALENDAR", "status": "ok"}]
    return []


def requests_used(runs: list[dict[str, Any]], day: str) -> int:
    return sum(
        len(_items(run)) for run in runs if str(run.get("as_of", "")).startswith(day)
    )


def calendar_collected(runs: list[dict[str, Any]], day: str) -> bool:
    return any(
        item.get("function") == "EARNINGS_CALENDAR" and item.get("status") == "ok"
        for run in runs
        if str(run.get("as_of", "")).startswith(day)
        for item in _items(run)
    )


def histories_from(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    ordered = sorted(runs, key=lambda run: str(run.get("as_of", "")))
    for run in ordered:
        for item in _items(run):
            if item.get("function") != "EARNINGS" or item.get("status") not in {
                "ok",
                "empty",
                "error",
            }:
                continue
            symbol = item.get("symbol")
            if not symbol:
                continue
            found[symbol] = {
                "fetched_at": run.get("as_of", ""),
                "latest_reported": item.get("latest_reported"),
                "empty": item.get("status") == "empty",
            }
    return found


def _market_day(now: datetime) -> date:
    return now.astimezone(ZoneInfo("America/New_York")).date()


def _fetched_on(value: str) -> date | None:
    if not value:
        return None
    try:
        return (
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            .astimezone(ZoneInfo("America/New_York"))
            .date()
        )
    except ValueError:
        return None


def choose_symbols(
    now: datetime,
    events: list[dict[str, Any]],
    securities: list[dict[str, Any]],
    features: list[dict[str, Any]],
    histories: dict[str, dict[str, Any]],
    room: int,
) -> list[str]:
    if room <= 0:
        return []
    identities = {row["symbol"]: row for row in securities}
    measured = {row["symbol"]: row.get("values") or {} for row in features}
    today = _market_day(now)
    chosen: dict[str, dict[str, Any]] = {}
    for event in events:
        symbol = event.get("symbol")
        identity = identities.get(symbol)
        if not symbol or not identity:
            continue
        if identity.get("asset_type") not in {None, "unverified", "common_stock"}:
            continue
        try:
            report = date.fromisoformat(event["report_date"])
        except (TypeError, ValueError, KeyError):
            continue
        if (
            not today - timedelta(days=RECENT_REPORT)
            <= report
            <= today + timedelta(days=LOOKAHEAD)
        ):
            continue
        history = histories.get(symbol)
        fetched = _fetched_on(history["fetched_at"]) if history else None
        if fetched == today:
            continue
        if history and report >= today and not history.get("empty"):
            continue
        if (
            history
            and history.get("empty")
            and report >= today
            and fetched
            and (today - fetched).days < 7
        ):
            continue
        latest = (history or {}).get("latest_reported")
        if report < today and latest and str(latest) >= report.isoformat():
            continue
        if report >= today and history is None:
            group = 0 if (report - today).days <= SOON else 1
        elif report < today:
            group = 2
        else:
            group = 3
        values = measured.get(symbol, {})
        ratio = values.get("vol_compression_ratio")
        momentum = values.get("return_20")
        setup = (
            0
            if (
                (ratio is not None and ratio < 0.8)
                or (momentum is not None and abs(momentum) >= 0.02)
            )
            else 1
        )
        common = 0 if identity.get("asset_type") == "common_stock" else 1
        current = chosen.get(symbol)
        candidate = {
            "group": group,
            "setup": setup,
            "common": common,
            "report": report.isoformat(),
            "symbol": symbol,
        }
        if current is None or (
            candidate["group"],
            candidate["report"],
        ) < (current["group"], current["report"]):
            chosen[symbol] = candidate
    ordered = sorted(
        chosen.values(),
        key=lambda row: (
            row["group"],
            row["setup"],
            row["common"],
            row["report"],
            row["symbol"],
        ),
    )
    return [row["symbol"] for row in ordered[:room]]


def plan(
    now: datetime,
    runs_today: list[dict[str, Any]],
    events: list[dict[str, Any]],
    securities: list[dict[str, Any]],
    features: list[dict[str, Any]],
    history_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    day = budget_day(now)
    used = requests_used(runs_today, day)
    room = max(0, LIMIT - SPARE - used)
    calendar = room > 0 and not calendar_collected(runs_today, day)
    if calendar:
        room -= 1
    symbols = choose_symbols(
        now, events, securities, features, histories_from(history_runs), room
    )
    return {
        "budget_day": day,
        "used": used,
        "calendar": calendar,
        "symbols": symbols,
        "limit": LIMIT,
        "spare": SPARE,
    }
