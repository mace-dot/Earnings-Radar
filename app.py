"""
Earnings Radar — local Streamlit MVP.

CSV-first earnings research dashboard. No live prices, no invented
estimates, no brokerage execution.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from earnings_radar.calculations import realized_pnl, straddle_purchase_cost
from earnings_radar.quote_selection import select_quote
from earnings_radar.validation import iso_date, ticker as validate_ticker
from zoneinfo import ZoneInfo
from datetime import datetime
from earnings_radar.config import (
    CONFIRMATION_STATUSES,
    EXPORTS_DIR,
    RESEARCH_NOTE_CATEGORIES,
    STALE_QUOTE_HOURS,
    WIDE_SPREAD_PCT,
)
from earnings_radar.db import (
    add_paper_trade,
    add_research_note,
    close_paper_trade,
    delete_research_note,
    fetch_all,
    get_conn,
    init_db,
)
from earnings_radar.export import build_research_packet
from earnings_radar.flags import annotate_radar_row
from earnings_radar.imports import (
    import_earnings_csv,
    import_options_csv,
    load_sample_data,
    read_sample_bytes,
    read_template_bytes,
)

st.set_page_config(
    page_title="Earnings Radar",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)


DISCLAIMER = (
    "Mechanical quote math only — not a calibrated forecast of the earnings move, "
    "not implied-move modeling, and not brokerage advice. All prices and dates come "
    "from your CSV imports."
)


@st.cache_resource
def _ensure_db() -> str:
    path = init_db()
    return str(path)


def _flags_cell(flags: list[str]) -> str:
    return "; ".join(flags) if flags else "—"


def page_radar() -> None:
    st.header("Radar — upcoming earnings")
    st.caption(DISCLAIMER)

    today = st.date_input("As-of date (upcoming filter)", value=datetime.now(ZoneInfo("America/New_York")).date())
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        status_filter = st.multiselect(
            "Confirmation status",
            options=list(CONFIRMATION_STATUSES),
            default=list(CONFIRMATION_STATUSES),
        )
    with col_b:
        only_flagged = st.checkbox("Only rows with any flags", value=False)
    with col_c:
        require_quote = st.checkbox("Only tickers with option quotes", value=False)

    with get_conn() as conn:
        events = fetch_all(
            conn,
            """
            SELECT * FROM earnings_events
            WHERE earnings_date >= ? AND superseded_by IS NULL
            ORDER BY earnings_date ASC, ticker ASC
            """,
            (today.isoformat(),),
        )
        note_counts = {
            r["ticker"]: r["n"]
            for r in fetch_all(
                conn,
                "SELECT ticker, COUNT(*) AS n FROM research_notes GROUP BY ticker",
            )
        }
        all_quotes = fetch_all(conn, "SELECT * FROM option_quotes ORDER BY ticker, id DESC")

    rows = []
    for ev in events:
        if ev["confirmation_status"] not in status_filter:
            continue
        q = select_quote(ev, all_quotes)
        if require_quote and not q:
            continue
        ann = annotate_radar_row(ev, q, note_counts.get(ev["ticker"], 0))
        if only_flagged and not (ann["research_flags"] or ann["liquidity_flags"]):
            continue
        rows.append(
            {
                "Ticker": ann["ticker"],
                "Earnings date": ann["earnings_date"],
                "Time": ann["earnings_time"],
                "Status": ann["confirmation_status"],
                "Spot": ann.get("stock_price"),
                "Strike": ann.get("strike"),
                "Expiration": ann.get("expiration"),
                "Call bid/ask": (
                    f"{ann.get('call_bid')} / {ann.get('call_ask')}"
                    if ann.get("has_quote")
                    else "—"
                ),
                "Put bid/ask": (
                    f"{ann.get('put_bid')} / {ann.get('put_ask')}"
                    if ann.get("has_quote")
                    else "—"
                ),
                "Call+put ask": ann.get("straddle_ask_cost"),
                "Contract $": ann.get("contract_cost"),
                "BE low / high": (
                    f"{ann.get('breakeven_low')} / {ann.get('breakeven_high')}"
                    if ann.get("breakeven_low") is not None
                    else "—"
                ),
                "Cost % spot": ann.get("straddle_cost_pct_of_spot"),
                "Research flags": _flags_cell(ann["research_flags"]),
                "Liquidity flags": _flags_cell(ann["liquidity_flags"]),
                "Notes": ann["note_count"],
                "Earnings source": ann.get("earnings_source") or "",
            }
        )

    st.info(
        f"Liquidity thresholds: stale > {STALE_QUOTE_HOURS:g}h, "
        f"wide spread ≥ {WIDE_SPREAD_PCT:g}% of mid. "
        "Research flags and liquidity flags are tracked separately."
    )

    if not rows:
        st.warning(
            "No upcoming earnings match these filters. "
            "Import a calendar CSV or load sample data from the Import page."
        )
        return

    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    with st.expander("How to read the numbers"):
        st.markdown(
            """
- **Call+put ask** — sum of call ask + put ask at the same strike (purchase cost per share).
- **Contract $** — that debit × 100.
- **BE low / high** — expiration breakevens for a long straddle at that debit
  (`strike ± call_ask + put_ask`). Not a predicted earnings move.
- **Research flags** — confirmation / source / notes completeness.
- **Liquidity flags** — stale quotes, missing fields, wide spreads,
  expiration before earnings, thin volume/OI.
            """
        )


def page_import() -> None:
    st.header("Import CSV data")
    st.caption(
        "Start here. Templates and sample files are labeled. "
        "Sample rows are fictional illustrations — not live market data."
    )

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Templates")
        st.download_button(
            "Download earnings calendar template",
            data=read_template_bytes("earnings_calendar_template.csv"),
            file_name="earnings_calendar_template.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download option chains template",
            data=read_template_bytes("option_chains_template.csv"),
            file_name="option_chains_template.csv",
            mime="text/csv",
        )
    with c2:
        st.subheader("Sample data (labeled SAMPLE)")
        st.download_button(
            "Download sample earnings calendar",
            data=read_sample_bytes("sample_earnings_calendar.csv"),
            file_name="sample_earnings_calendar.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download sample option chains",
            data=read_sample_bytes("sample_option_chains.csv"),
            file_name="sample_option_chains.csv",
            mime="text/csv",
        )
        if st.button("Load sample data into local DB", type="primary"):
            result = load_sample_data(replace=True)
            st.info("Samples loaded into the separate demo database. Switch to Demo mode in the sidebar to view them.")
            if result["ok"]:
                st.success(
                    f"Loaded {result['earnings_imported']} earnings rows and "
                    f"{result['options_imported']} option rows (SAMPLE DATA)."
                )
            else:
                st.error("Sample load failed:\n" + "\n".join(result["errors"]))

    st.divider()
    st.subheader("Upload your CSVs")

    replace = st.checkbox("Replace existing rows of that type on import", value=False)

    earn_file = st.file_uploader("Earnings calendar CSV", type=["csv"], key="earn_up")
    if earn_file and st.button("Import earnings calendar"):
        result = import_earnings_csv(earn_file, replace=replace)
        if result["ok"]:
            st.success(f"Imported {result['imported']} earnings events.")
        else:
            st.error("Import errors:\n" + "\n".join(result["errors"]))

    opt_file = st.file_uploader("Option chains CSV", type=["csv"], key="opt_up")
    if opt_file and st.button("Import option chains"):
        result = import_options_csv(opt_file, replace=replace)
        if result["ok"]:
            st.success(f"Imported {result['imported']} option quotes.")
        else:
            st.error("Import errors:\n" + "\n".join(result["errors"]))

    st.divider()
    with get_conn() as conn:
        n_e = conn.execute("SELECT COUNT(*) AS n FROM earnings_events").fetchone()["n"]
        n_o = conn.execute("SELECT COUNT(*) AS n FROM option_quotes").fetchone()["n"]
    st.write(f"Database currently holds **{n_e}** earnings events and **{n_o}** option quotes.")


def page_quotes() -> None:
    st.header("Option quotes detail")
    st.caption(DISCLAIMER)

    with get_conn() as conn:
        tickers = [
            r["ticker"]
            for r in fetch_all(conn, "SELECT DISTINCT ticker FROM option_quotes ORDER BY ticker")
        ]
        events = {
            r["ticker"]: r
            for r in fetch_all(conn, "SELECT * FROM earnings_events")
        }

    if not tickers:
        st.warning("No option quotes yet. Import a CSV or load sample data.")
        return

    ticker = st.selectbox("Ticker", tickers)
    with get_conn() as conn:
        quotes = fetch_all(
            conn,
            "SELECT * FROM option_quotes WHERE ticker = ? ORDER BY expiration, strike",
            (ticker,),
        )

    ev = events.get(ticker)
    rows = []
    for q in quotes:
        ann = annotate_radar_row(
            ev
            or {
                "ticker": ticker,
                "earnings_date": None,
                "earnings_time": "Unknown",
                "confirmation_status": "Unconfirmed",
                "source": "",
            },
            q,
            0,
        )
        rows.append(
            {
                "Strike": ann.get("strike"),
                "Expiration": ann.get("expiration"),
                "Spot": ann.get("stock_price"),
                "Call bid": ann.get("call_bid"),
                "Call ask": ann.get("call_ask"),
                "Call spread %": ann.get("call_spread_pct"),
                "Put bid": ann.get("put_bid"),
                "Put ask": ann.get("put_ask"),
                "Put spread %": ann.get("put_spread_pct"),
                "Call+put ask": ann.get("straddle_ask_cost"),
                "Contract $": ann.get("contract_cost"),
                "BE low": ann.get("breakeven_low"),
                "BE high": ann.get("breakeven_high"),
                "Cost % spot": ann.get("straddle_cost_pct_of_spot"),
                "Quote time": ann.get("quote_timestamp"),
                "Vol C/P": f"{ann.get('call_volume')} / {ann.get('put_volume')}",
                "OI C/P": f"{ann.get('call_open_interest')} / {ann.get('put_open_interest')}",
                "Liquidity flags": _flags_cell(ann["liquidity_flags"]),
                "Source": ann.get("quote_source") or "",
            }
        )

    if ev:
        st.write(
            f"Linked earnings: **{ev['earnings_date']} {ev['earnings_time']}** "
            f"({ev['confirmation_status']}) — source: {ev['source'] or 'n/a'}"
        )
    else:
        st.write("No earnings event linked for this ticker.")

    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def page_research() -> None:
    st.header("Research notes")
    st.caption(
        "Attach source links and notes on guidance, peers, customers, margins, "
        "and contradictory evidence. Kept separate from options liquidity."
    )

    with get_conn() as conn:
        tickers = sorted(
            {
                r["ticker"]
                for r in fetch_all(
                    conn,
                    """
                    SELECT ticker FROM earnings_events
                    UNION SELECT ticker FROM option_quotes
                    UNION SELECT ticker FROM research_notes
                    """,
                )
            }
        )

    ticker = st.selectbox("Ticker", tickers or [""], key="note_ticker")
    if not ticker:
        st.info("Import data first, or type a ticker below when adding a note.")

    with st.form("add_note"):
        st.subheader("Add note")
        t = st.text_input("Ticker", value=ticker or "").upper().strip()
        category = st.selectbox("Category", RESEARCH_NOTE_CATEGORIES)
        source_url = st.text_input("Source URL")
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save note")
        if submitted:
            if not t:
                st.error("Ticker is required.")
            else:
                with get_conn() as conn:
                    add_research_note(conn, t, category, source_url, notes)
                st.success(f"Saved note for {t}.")
                st.rerun()

    if ticker:
        with get_conn() as conn:
            notes_rows = fetch_all(
                conn,
                """
                SELECT * FROM research_notes
                WHERE ticker = ?
                ORDER BY category, updated_at DESC
                """,
                (ticker,),
            )
        if not notes_rows:
            st.write("_No notes for this ticker yet._")
        else:
            for n in notes_rows:
                with st.expander(f"[{n['category']}] {n['source_url'] or '(no link)'} — #{n['id']}"):
                    st.write(n["notes"] or "_empty_")
                    if st.button("Delete", key=f"del_note_{n['id']}"):
                        with get_conn() as conn:
                            delete_research_note(conn, n["id"])
                        st.rerun()


def page_export() -> None:
    st.header("Export research packet")
    st.caption(
        "Concise markdown for ChatGPT / Claude. Includes disclaimer that numbers "
        "are not a calibrated earnings-move forecast."
    )

    with get_conn() as conn:
        tickers = sorted(
            {
                r["ticker"]
                for r in fetch_all(
                    conn,
                    """
                    SELECT ticker FROM earnings_events
                    UNION SELECT ticker FROM option_quotes
                    UNION SELECT ticker FROM research_notes
                    """,
                )
            }
        )

    if not tickers:
        st.warning("Nothing to export yet.")
        return

    ticker = st.selectbox("Ticker", tickers)
    packet = build_research_packet(ticker)
    st.code(packet, language="markdown")

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_name = f"{ticker}_research_packet.md"
    st.download_button(
        "Download markdown packet",
        data=packet.encode("utf-8"),
        file_name=out_name,
        mime="text/markdown",
    )
    if st.button("Also save under exports/"):
        path = EXPORTS_DIR / out_name
        path.write_text(packet, encoding="utf-8")
        st.success(f"Wrote {path}")


def page_journal() -> None:
    st.header("Paper-trade journal")
    st.caption(
        "Track thesis, invalidation, entry/exit quotes, fees, and realized P&L. "
        "No brokerage execution."
    )

    with st.form("open_trade"):
        st.subheader("Open paper trade")
        c1, c2, c3 = st.columns(3)
        with c1:
            ticker = st.text_input("Ticker").upper().strip()
            strategy = st.selectbox(
                "Strategy",
                [
                    "long_straddle",
                    "long_call",
                    "long_put",
                ],
            )
            contracts = st.number_input("Contracts", min_value=1, value=1)
        with c2:
            strike = st.number_input("Strike", min_value=0.0, value=100.0, format="%.2f")
            expiration = st.text_input("Expiration (YYYY-MM-DD)", value="")
            entry_date = st.date_input("Entry date", value=datetime.now(ZoneInfo("America/New_York")).date())
        with c3:
            entry_call_ask = st.number_input("Entry call ask", min_value=0.0, value=0.0, format="%.2f")
            entry_put_ask = st.number_input("Entry put ask", min_value=0.0, value=0.0, format="%.2f")
            fees = st.number_input("Fees ($)", min_value=0.0, value=0.0, format="%.2f")

        thesis = st.text_area("Thesis")
        invalidation = st.text_area("Invalidation conditions")
        notes = st.text_area("Notes")

        if strategy == "long_straddle":
            debit = straddle_purchase_cost(entry_call_ask, entry_put_ask)
        elif strategy == "long_call":
            debit = entry_call_ask
        elif strategy == "long_put":
            debit = entry_put_ask
        else:
            debit = (entry_call_ask or 0) + (entry_put_ask or 0)

        st.write(f"Computed entry debit (per share): **{debit}**")
        submitted = st.form_submit_button("Log open trade")
        if submitted:
            validation_error = None
            try:
                validate_ticker(ticker)
                expiration = iso_date(expiration)
                if strike <= 0 or expiration < entry_date.isoformat():
                    raise ValueError('Positive strike and expiration on/after entry date required.')
            except (TypeError, ValueError) as exc:
                validation_error = str(exc)
            if validation_error:
                st.error(validation_error)
            else:
                with get_conn() as conn:
                    add_paper_trade(
                        conn,
                        {
                            "ticker": ticker,
                            "strategy": strategy,
                            "strike": strike,
                            "expiration": iso_date(expiration),
                            "contracts": int(contracts),
                            "entry_date": entry_date.isoformat(),
                            "entry_call_ask": entry_call_ask,
                            "entry_put_ask": entry_put_ask,
                            "entry_debit": debit,
                            "fees": fees,
                            "thesis": thesis,
                            "invalidation": invalidation,
                            "status": "open",
                            "notes": notes,
                        },
                    )
                st.success(f"Opened paper trade for {ticker}.")
                st.rerun()

    st.divider()
    with get_conn() as conn:
        trades = fetch_all(
            conn,
            "SELECT * FROM paper_trades ORDER BY status DESC, entry_date DESC, id DESC",
        )

    if not trades:
        st.info("No paper trades yet.")
        return

    st.subheader("Journal")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "ID": t["id"],
                    "Ticker": t["ticker"],
                    "Strategy": t["strategy"],
                    "Status": t["status"],
                    "Entry": t["entry_date"],
                    "Exit": t.get("exit_date") or "",
                    "Entry debit": t.get("entry_debit"),
                    "Exit credit": t.get("exit_credit"),
                    "Fees": t.get("fees"),
                    "Realized P&L": t.get("realized_pnl"),
                    "Thesis": t.get("thesis"),
                    "Invalidation": t.get("invalidation"),
                }
                for t in trades
            ]
        ),
        width="stretch",
        hide_index=True,
    )

    open_trades = [t for t in trades if t["status"] == "open"]
    if open_trades:
        st.subheader("Close a trade")
        labels = {
            t["id"]: f"#{t['id']} {t['ticker']} {t['strategy']} @ {t['entry_debit']}"
            for t in open_trades
        }
        trade_id = st.selectbox(
            "Open trade",
            options=list(labels.keys()),
            format_func=lambda i: labels[i],
        )
        selected = next(t for t in open_trades if t["id"] == trade_id)
        c1, c2, c3 = st.columns(3)
        with c1:
            exit_date = st.date_input("Exit date", value=datetime.now(ZoneInfo("America/New_York")).date(), key="exit_date")
            exit_call_bid = st.number_input("Exit call bid", min_value=0.0, value=0.0, format="%.2f")
        with c2:
            exit_put_bid = st.number_input("Exit put bid", min_value=0.0, value=0.0, format="%.2f")
            exit_fees = st.number_input(
                "Total fees ($)",
                min_value=0.0,
                value=float(selected.get("fees") or 0),
                format="%.2f",
            )
        with c3:
            if selected["strategy"] == "long_call":
                credit = exit_call_bid
            elif selected["strategy"] == "long_put":
                credit = exit_put_bid
            else:
                credit = (exit_call_bid or 0) + (exit_put_bid or 0)
            pnl = realized_pnl(
                selected.get("entry_debit"),
                credit,
                contracts=int(selected.get("contracts") or 1),
                fees=exit_fees,
            )
            st.metric("Exit credit (per share)", f"{credit:.2f}")
            st.metric("Realized P&L ($)", f"{pnl:.2f}" if pnl is not None else "n/a")

        close_notes = st.text_input("Close notes", value=selected.get("notes") or "")
        if st.button("Close trade", type="primary"):
            with get_conn() as conn:
                close_paper_trade(
                    conn,
                    trade_id,
                    exit_date.isoformat(),
                    exit_call_bid,
                    exit_put_bid,
                    float(credit),
                    float(exit_fees),
                    float(pnl) if pnl is not None else 0.0,
                    close_notes,
                )
            st.success(f"Closed trade #{trade_id}. Realized P&L: {pnl}")
            st.rerun()


def page_about() -> None:
    st.header("About Earnings Radar")
    st.markdown(
        f"""
**Earnings Radar** is a local MVP for earnings research around option packages.

### What it does
- Import an earnings calendar and option-chain snapshots via CSV
- Flag research-quality issues and options-liquidity issues **separately**
- Compute spread %, same-strike call+put ask cost, contract cost, and expiration breakevens
- Attach source links / notes (guidance, peers, customers, margins, contradictory evidence)
- Export a concise research packet for ChatGPT or Claude
- Keep a paper-trade journal with thesis, invalidation, fees, and realized P&L

### What it deliberately does **not** do
- Fetch or fabricate live prices, estimates, or earnings dates
- Present costs as a calibrated forecast of the earnings move
- Invent breakout probabilities
- Execute brokerage orders
- Store API keys in source control (see `.env.example` for future live-data hooks)

### Local database
`{_ensure_db()}`

### Thresholds
- Stale quote: > {STALE_QUOTE_HOURS:g} hours
- Wide spread: ≥ {WIDE_SPREAD_PCT:g}% of mid
        """
    )


def main() -> None:
    import earnings_radar.db as db
    from earnings_radar.config import DATA_DIR, DB_PATH
    mode = st.sidebar.selectbox('Operating mode', ['Research', 'Demo'])
    db.DB_OVERRIDE.set(DATA_DIR / 'demo.db' if mode == 'Demo' else DB_PATH)
    init_db()
    st.sidebar.caption('SAMPLE DATA — isolated demo storage' if mode == 'Demo' else 'Real research — no sample fallback')
    st.sidebar.title("Earnings Radar")
    st.sidebar.caption("Local CSV → SQLite research MVP")
    page = st.sidebar.radio(
        "Navigate",
        [
            "Today",
            "Opportunities",
            "Earnings",
            "Systemic Risk",
            "Evidence",
            "Connections",
            "Radar",
            "Import",
            "Option quotes",
            "Research notes",
            "Export packet",
            "Paper journal",
            "About",
        ],
    )
    st.sidebar.markdown("---")
    st.sidebar.caption(DISCLAIMER)

    from earnings_radar import research_ui
    pages = {
        "Today": research_ui.today,
        "Evidence": research_ui.evidence_page,
        "Connections": research_ui.connections,
        "Earnings": lambda: research_ui.earnings(page_radar),
        "Opportunities": research_ui.opportunities,
        "Systemic Risk": research_ui.systemic_page,
        "Radar": page_radar,
        "Import": page_import,
        "Option quotes": page_quotes,
        "Research notes": page_research,
        "Export packet": page_export,
        "Paper journal": page_journal,
        "About": page_about,
    }
    if mode == "Demo" and page in {"Today","Evidence","Connections","Systemic Risk"}:
        st.info("Switch to Research mode to view the real research database. Demo imports remain isolated.")
    else:
        pages[page]()


if __name__ == "__main__":
    main()
