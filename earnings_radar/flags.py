"""
Research-quality and options-liquidity flags.

These two concerns stay separate on purpose:
- Research quality: earnings date confirmation, source, attached notes.
- Options liquidity: quote freshness, completeness, spreads, volume/OI,
  and whether expiration is before the earnings event.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from earnings_radar.calculations import enrich_quote_row, spread_pct


def _num(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
from earnings_radar.config import (
    LOW_OPEN_INTEREST,
    LOW_VOLUME,
    STALE_QUOTE_HOURS,
    WIDE_SPREAD_PCT,
)


def _parse_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(text[:19] if len(text) >= 19 else text, fmt)
                    break
                except ValueError:
                    dt = None
            else:
                return None
            if dt is None:
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def research_quality_flags(event: dict[str, Any], note_count: int = 0) -> list[str]:
    """Flags about research completeness — not about option liquidity."""
    flags: list[str] = []
    status = (event.get("confirmation_status") or "").strip()
    if status in ("", "Unconfirmed"):
        flags.append("unconfirmed_earnings")
    elif status == "Estimated":
        flags.append("estimated_earnings")
    if not (event.get("source") or "").strip():
        flags.append("missing_earnings_source")
    if note_count == 0:
        flags.append("no_research_notes")
    return flags


def liquidity_flags(
    quote: dict[str, Any],
    earnings_date: Optional[Any] = None,
    *,
    now: Optional[datetime] = None,
    stale_hours: float = STALE_QUOTE_HOURS,
    wide_spread_pct: float = WIDE_SPREAD_PCT,
) -> list[str]:
    """Flags about option quote usability / liquidity."""
    flags: list[str] = []
    now = now or datetime.now(timezone.utc)

    required = {
        "stock_price": quote.get("stock_price"),
        "strike": quote.get("strike"),
        "expiration": quote.get("expiration"),
        "call_bid": quote.get("call_bid"),
        "call_ask": quote.get("call_ask"),
        "put_bid": quote.get("put_bid"),
        "put_ask": quote.get("put_ask"),
        "quote_timestamp": quote.get("quote_timestamp"),
    }
    missing = [k for k, v in required.items() if v is None or v == ""]
    if missing:
        flags.append("missing_fields:" + ",".join(missing))

    ts = _parse_timestamp(quote.get("quote_timestamp"))
    if ts is None:
        flags.append("missing_quote_timestamp")
    else:
        age = now - ts.astimezone(timezone.utc)
        if age > timedelta(hours=stale_hours):
            flags.append(f"stale_quote:{age.total_seconds() / 3600:.1f}h")

    for side, bid_key, ask_key in (
        ("call", "call_bid", "call_ask"),
        ("put", "put_bid", "put_ask"),
    ):
        sp = spread_pct(quote.get(bid_key), quote.get(ask_key))
        if sp is not None and sp >= wide_spread_pct:
            flags.append(f"wide_{side}_spread:{sp:.1f}%")

    exp = _parse_date(quote.get("expiration"))
    earn = _parse_date(earnings_date)
    if exp and earn and exp < earn:
        flags.append("expiration_before_earnings")

    call_vol = _num(quote.get("call_volume"))
    put_vol = _num(quote.get("put_volume"))
    if call_vol is not None and put_vol is not None:
        if call_vol < LOW_VOLUME and put_vol < LOW_VOLUME:
            flags.append("low_volume")
    call_oi = _num(quote.get("call_open_interest"))
    put_oi = _num(quote.get("put_open_interest"))
    if call_oi is not None and put_oi is not None:
        if call_oi < LOW_OPEN_INTEREST and put_oi < LOW_OPEN_INTEREST:
            flags.append("low_open_interest")

    return flags


def annotate_radar_row(
    event: dict[str, Any],
    quote: Optional[dict[str, Any]],
    note_count: int,
    *,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Merge event + optional quote with separate research/liquidity flag sets."""
    row: dict[str, Any] = {
        "ticker": event.get("ticker"),
        "earnings_date": event.get("earnings_date"),
        "earnings_time": event.get("earnings_time"),
        "confirmation_status": event.get("confirmation_status"),
        "earnings_source": event.get("source"),
        "note_count": note_count,
        "research_flags": research_quality_flags(event, note_count),
        "liquidity_flags": [],
        "has_quote": quote is not None,
    }
    if quote:
        enriched = enrich_quote_row(quote)
        row.update(
            {
                "stock_price": enriched.get("stock_price"),
                "strike": enriched.get("strike"),
                "expiration": enriched.get("expiration"),
                "call_bid": enriched.get("call_bid"),
                "call_ask": enriched.get("call_ask"),
                "put_bid": enriched.get("put_bid"),
                "put_ask": enriched.get("put_ask"),
                "quote_timestamp": enriched.get("quote_timestamp"),
                "call_volume": enriched.get("call_volume"),
                "put_volume": enriched.get("put_volume"),
                "call_open_interest": enriched.get("call_open_interest"),
                "put_open_interest": enriched.get("put_open_interest"),
                "quote_source": enriched.get("source"),
                "call_spread_pct": enriched.get("call_spread_pct"),
                "put_spread_pct": enriched.get("put_spread_pct"),
                "straddle_ask_cost": enriched.get("straddle_ask_cost"),
                "contract_cost": enriched.get("contract_cost"),
                "breakeven_low": enriched.get("breakeven_low"),
                "breakeven_high": enriched.get("breakeven_high"),
                "straddle_cost_pct_of_spot": enriched.get("straddle_cost_pct_of_spot"),
            }
        )
        row["liquidity_flags"] = liquidity_flags(
            quote, event.get("earnings_date"), now=now
        )
    else:
        row["liquidity_flags"] = ["no_option_quote"]
    row["research_flag_count"] = len(row["research_flags"])
    row["liquidity_flag_count"] = len(row["liquidity_flags"])
    return row
