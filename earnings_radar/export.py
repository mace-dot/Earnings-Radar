"""Concise research packet export for ChatGPT / Claude."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from earnings_radar.calculations import enrich_quote_row
from earnings_radar.db import fetch_all, get_conn, init_db
from earnings_radar.flags import annotate_radar_row
from earnings_radar.quote_selection import select_quote


DISCLAIMER = (
    "DISCLAIMER: Figures below are mechanical quote arithmetic from user-imported "
    "CSV data. They are NOT calibrated forecasts of the earnings move, implied-move "
    "models, breakout probabilities, or brokerage recommendations. Verify all dates, "
    "prices, and sources independently before acting."
)


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None or value == "":
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def build_research_packet(ticker: str) -> str:
    """Build a concise markdown research packet for one ticker."""
    init_db()
    t = ticker.upper().strip()
    with get_conn() as conn:
        events = fetch_all(
            conn,
            """
            SELECT * FROM earnings_events
            WHERE ticker = ? AND superseded_by IS NULL
            ORDER BY earnings_date DESC
            """,
            (t,),
        )
        quotes = fetch_all(
            conn,
            """
            SELECT * FROM option_quotes
            WHERE ticker = ?
            ORDER BY quote_timestamp DESC, id DESC
            """,
            (t,),
        )
        notes = fetch_all(
            conn,
            """
            SELECT * FROM research_notes
            WHERE ticker = ?
            ORDER BY category, updated_at DESC
            """,
            (t,),
        )
        trades = fetch_all(
            conn,
            """
            SELECT * FROM paper_trades
            WHERE ticker = ?
            ORDER BY entry_date DESC
            """,
            (t,),
        )

    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    lines: list[str] = [
        f"# Earnings Radar Research Packet — {t}",
        "",
        f"Generated (UTC): {generated}",
        "",
        DISCLAIMER,
        "",
        "## Earnings event(s)",
    ]

    if not events:
        lines.append("_No earnings events imported for this ticker._")
    else:
        for ev in events:
            note_count = len(notes)
            # Prefer latest quote for flag annotation
            q = select_quote(ev, quotes)
            ann = annotate_radar_row(ev, q, note_count)
            lines.extend(
                [
                    f"- **Date:** {ev['earnings_date']} ({ev['earnings_time']})",
                    f"- **Confirmation:** {ev['confirmation_status']}",
                    f"- **Source:** {ev['source'] or 'n/a'}",
                    f"- **Selected quote ID:** {q['id'] if q else 'none eligible'}",
                    f"- **Research flags:** {', '.join(ann['research_flags']) or 'none'}",
                    "",
                ]
            )

    lines.append("## Option quotes (imported)")
    if not quotes:
        lines.append("_No option quotes imported._")
    else:
        lines.append(
            "_Same-strike call+put cost uses ask prices. Breakevens are expiration "
            "breakevens for a long straddle at that debit — not a predicted move._"
        )
        lines.append("")
        for q in quotes[:8]:
            e = enrich_quote_row(q)
            ann = annotate_radar_row(
                events[0]
                if events
                else {
                    "ticker": t,
                    "earnings_date": None,
                    "earnings_time": "Unknown",
                    "confirmation_status": "Unconfirmed",
                    "source": "",
                },
                q,
                len(notes),
            )
            lines.extend(
                [
                    f"### Strike {_fmt(e['strike'])} / Exp {e['expiration']}",
                    f"- Spot (imported): {_fmt(e.get('stock_price'))}",
                    f"- Call bid/ask: {_fmt(e.get('call_bid'))} / {_fmt(e.get('call_ask'))} "
                    f"(spread {_fmt(e.get('call_spread_pct'))}%)",
                    f"- Put bid/ask: {_fmt(e.get('put_bid'))} / {_fmt(e.get('put_ask'))} "
                    f"(spread {_fmt(e.get('put_spread_pct'))}%)",
                    f"- Call+put ask cost (per share): {_fmt(e.get('straddle_ask_cost'))}",
                    f"- Contract cost (x100): {_fmt(e.get('contract_cost'))}",
                    f"- Expiration breakevens: {_fmt(e.get('breakeven_low'))} / "
                    f"{_fmt(e.get('breakeven_high'))}",
                    f"- Cost as % of spot: {_fmt(e.get('straddle_cost_pct_of_spot'))}%",
                    f"- Volume C/P: {_fmt(e.get('call_volume'), 0)} / {_fmt(e.get('put_volume'), 0)}",
                    f"- OI C/P: {_fmt(e.get('call_open_interest'), 0)} / "
                    f"{_fmt(e.get('put_open_interest'), 0)}",
                    f"- Quote timestamp: {e.get('quote_timestamp') or 'n/a'}",
                    f"- Quote source: {e.get('source') or 'n/a'}",
                    f"- Liquidity flags: {', '.join(ann['liquidity_flags']) or 'none'}",
                    "",
                ]
            )

    lines.append("## Research notes")
    if not notes:
        lines.append("_No research notes attached._")
    else:
        by_cat: dict[str, list[dict[str, Any]]] = {}
        for n in notes:
            by_cat.setdefault(n["category"], []).append(n)
        for cat, items in by_cat.items():
            lines.append(f"### {cat}")
            for n in items:
                url = n["source_url"] or "(no link)"
                lines.append(f"- Source: {url}")
                if n["notes"]:
                    lines.append(f"  - {n['notes']}")
            lines.append("")

    lines.append("## Paper trades (journal)")
    if not trades:
        lines.append("_No paper trades logged._")
    else:
        for tr in trades:
            lines.extend(
                [
                    f"- **{tr['status'].upper()}** {tr['strategy']} | entry {tr['entry_date']}"
                    + (f" | exit {tr['exit_date']}" if tr.get("exit_date") else ""),
                    f"  - Entry debit: {_fmt(tr.get('entry_debit'))} | "
                    f"Exit credit: {_fmt(tr.get('exit_credit'))} | "
                    f"Fees: {_fmt(tr.get('fees'))} | "
                    f"Realized P&L: {_fmt(tr.get('realized_pnl'))}",
                    f"  - Thesis: {tr.get('thesis') or 'n/a'}",
                    f"  - Invalidation: {tr.get('invalidation') or 'n/a'}",
                ]
            )

    lines.extend(
        [
            "",
            "## Suggested LLM prompt framing",
            "Summarize conflicting evidence, list what is confirmed vs estimated, "
            "and separate research quality from options liquidity. Do not invent "
            "prices, earnings dates, or probabilities.",
            "",
        ]
    )
    return "\n".join(lines)


def upcoming_tickers(as_of: Optional[date] = None) -> list[str]:
    init_db()
    today = (as_of or date.today()).isoformat()
    with get_conn() as conn:
        rows = fetch_all(
            conn,
            """
            SELECT DISTINCT ticker FROM earnings_events
            WHERE earnings_date >= ?
            ORDER BY ticker
            """,
            (today,),
        )
    return [r["ticker"] for r in rows]
