"""Point-in-time context for the large-move model. Missing inputs stay missing."""

from datetime import date, datetime, timedelta
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

VALUE_KEYS = (
    "days_to_report",
    "volume_multiple_20",
    "range_multiple_20",
    "implied_move",
    "spy_return_5",
    "spy_rv_60",
    "last_surprise",
    "beat_rate_4",
)


def known_name(key: str) -> str:
    return f"{key}_known"


def _field(key: str, value: float | int | None, known: bool) -> dict[str, Any]:
    return {key: value if known else None, known_name(key): 1 if known else 0}


def _market_day(as_of: datetime) -> date:
    return as_of.astimezone(ZoneInfo("America/New_York")).date()


def _stamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def days_to_report(events: list[dict[str, Any]], as_of: datetime) -> dict[str, Any]:
    today = _market_day(as_of)
    upcoming = []
    for event in events:
        try:
            report = date.fromisoformat(str(event.get("report_date")))
        except ValueError:
            continue
        if report >= today:
            upcoming.append((report, event))
    if not upcoming:
        return _field("days_to_report", None, False)
    report, event = min(upcoming, key=lambda item: item[0])
    dated = {
        source.get("date")
        for source in event.get("sources") or []
        if source.get("source") in {"Finnhub", "Alpha Vantage"} and source.get("date")
    }
    if event.get("date_status") == "conflicting" or len(dated) > 1:
        return _field("days_to_report", None, False)
    return _field("days_to_report", (report - today).days, True)


def _true_range(bar: dict[str, Any], previous_close: float) -> float | None:
    high, low = bar.get("h", bar.get("high")), bar.get("l", bar.get("low"))
    if high is None or low is None:
        return None
    return max(
        float(high) - float(low),
        abs(float(high) - previous_close),
        abs(float(low) - previous_close),
    )


def trading_multiples(bars: list[dict[str, Any]]) -> dict[str, Any]:
    """Latest session versus the previous 20. The latest session is not part of its baseline."""
    output = {
        **_field("volume_multiple_20", None, False),
        **_field("range_multiple_20", None, False),
    }
    if len(bars) < 22:
        return output
    tail = bars[-22:]
    volumes = [bar.get("v", bar.get("volume")) for bar in tail[-21:-1]]
    latest_volume = tail[-1].get("v", tail[-1].get("volume"))
    if latest_volume is not None and all(
        volume is not None and float(volume) > 0 for volume in volumes
    ):
        baseline = median(float(volume) for volume in volumes)
        if baseline > 0:
            output.update(
                _field("volume_multiple_20", float(latest_volume) / baseline, True)
            )
    ranges = []
    for previous, bar in zip(tail, tail[1:]):
        close = previous.get("c", previous.get("close"))
        if close is None:
            ranges.append(None)
            continue
        ranges.append(_true_range(bar, float(close)))
    if len(ranges) == 21 and all(value is not None and value > 0 for value in ranges):
        baseline = median(ranges[:-1])
        if baseline > 0:
            output.update(_field("range_multiple_20", ranges[-1] / baseline, True))
    return output


def saved_implied_move(
    rows: list[dict[str, Any]], report_date: str | None, as_of: datetime
) -> dict[str, Any]:
    usable = [
        row
        for row in rows
        if _stamp(row["observed_at"]) <= as_of
        and _stamp(row.get("retrieved_at") or row["observed_at"]) <= as_of
    ]
    if not usable or not report_date:
        return _field("implied_move", None, False)
    latest = max(usable, key=lambda row: row["observed_at"])
    payload = latest.get("payload") or {}
    move = payload.get("implied_move")
    if payload.get("report_date") != report_date or move is None:
        return _field("implied_move", None, False)
    return _field("implied_move", float(move), True)


def earnings_memory(rows: list[dict[str, Any]], as_of: datetime) -> dict[str, Any]:
    saved = []
    for row in rows:
        if _stamp(row["as_of"]) > as_of:
            continue
        payload = row.get("payload") or {}
        reported = payload.get("reported_date")
        try:
            reported_day = date.fromisoformat(str(reported))
        except ValueError:
            continue
        if reported_day > _market_day(as_of):
            continue
        saved.append(payload)
    saved.sort(key=lambda item: item["reported_date"])
    surprise = saved[-1].get("surprise") if saved else None
    paired = [
        item
        for item in saved
        if item.get("reported_eps") is not None
        and item.get("estimated_eps") is not None
    ]
    last_four = paired[-4:]
    beat = (
        sum(item["reported_eps"] > item["estimated_eps"] for item in last_four) / 4
        if len(last_four) == 4
        else None
    )
    return {
        **_field("last_surprise", surprise, surprise is not None),
        **_field("beat_rate_4", beat, beat is not None),
    }


def spy_market(store: Any, as_of: datetime) -> dict[str, Any]:
    """One shared market reading from bars already stored. Missing stays missing."""
    from engine.features import price_features
    from engine.move_features import setup_features
    from engine.providers.base import Observation

    rows = list(
        reversed(
            store.read(
                "daily_bars",
                {"symbol": "eq.SPY", "order": "session_date.desc", "limit": "80"},
            )
        )
    )
    if len(rows) < 61:
        try:
            archived = store.rpc(
                "radar_history_bars",
                {
                    "p_symbols": ["SPY"],
                    "p_start": (as_of - timedelta(days=200)).date().isoformat(),
                    "p_end": as_of.date().isoformat(),
                },
            )
        except Exception:
            archived = []
        if len(archived) >= len(rows):
            rows = archived
    observations = []
    for row in rows:
        observed = row.get("observed_at")
        available = row.get("available_at") or observed
        close = row.get("close", row.get("c"))
        if not observed or close is None:
            continue
        observations.append(
            Observation(
                "SPY",
                _stamp(str(observed)),
                _stamp(str(available)),
                row.get("source") or "Massive",
                {
                    "c": close,
                    "h": row.get("high", row.get("h")),
                    "l": row.get("low", row.get("l")),
                    "v": row.get("volume", row.get("v")),
                },
                row.get("feed") or "massive_daily_adjusted",
            )
        )
    if len(observations) < 21:
        return {}
    price = price_features(observations, as_of)
    setup = setup_features(observations, as_of)
    return {"return_5": price.get("return_5"), "rv_60": setup.get("rv_60")}


def load_context(store: Any, symbols: list[str], as_of: datetime) -> dict[str, Any]:
    if not symbols:
        return {"events": {}, "revisions": {}, "implied": {}, "spy": {}}
    membership = "in.(" + ",".join(symbols) + ")"
    market_day = _market_day(as_of).isoformat()
    events: dict[str, list] = {}
    revisions: dict[str, list] = {}
    implied: dict[str, list] = {}
    for row in store.pages(
        "earnings_events",
        {
            "symbol": membership,
            "report_date": f"gte.{market_day}",
            "order": "report_date.asc,id.asc",
        },
    ):
        events.setdefault(row["symbol"], []).append(row)
    for row in store.pages(
        "estimate_revisions",
        {
            "symbol": membership,
            "source": "eq.Alpha Vantage",
            "order": "as_of.asc,id.asc",
        },
    ):
        revisions.setdefault(row["symbol"], []).append(row)
    for row in store.pages(
        "market_observations",
        {
            "symbol": membership,
            "feed": "eq.cboe_delayed_implied",
            "order": "observed_at.asc,id.asc",
        },
    ):
        implied.setdefault(row["symbol"], []).append(row)
    return {
        "events": events,
        "revisions": revisions,
        "implied": implied,
        "spy": spy_market(store, as_of),
    }


def bar_values(observations: list[Any], as_of: datetime) -> list[dict[str, Any]]:
    rows = []
    for item in observations:
        if item.available_at > as_of or item.observed_at > as_of:
            continue
        rows.append((item.observed_at, item.values))
    rows.sort(key=lambda pair: pair[0])
    return [values for _, values in rows]


def context_features(
    bars: list[dict[str, Any]],
    events: list[dict[str, Any]],
    revisions: list[dict[str, Any]],
    implied_rows: list[dict[str, Any]],
    spy: dict[str, Any],
    as_of: datetime,
) -> dict[str, Any]:
    schedule = days_to_report(events, as_of)
    report_date = None
    if schedule["days_to_report_known"]:
        report_date = (
            _market_day(as_of) + timedelta(days=schedule["days_to_report"])
        ).isoformat()
    spy_return = spy.get("return_5")
    spy_vol = spy.get("rv_60")
    return {
        "context_version": "context-v1",
        **schedule,
        **trading_multiples(bars),
        **saved_implied_move(implied_rows, report_date, as_of),
        **_field("spy_return_5", spy_return, spy_return is not None),
        **_field("spy_rv_60", spy_vol, spy_vol is not None),
        **earnings_memory(revisions, as_of),
    }
