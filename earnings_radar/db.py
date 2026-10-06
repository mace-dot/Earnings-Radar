"""SQLite persistence for Earnings Radar."""

from __future__ import annotations

import sqlite3
import json
from contextvars import ContextVar
DB_OVERRIDE = ContextVar("earnings_radar_db_override", default=None)
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from earnings_radar.config import DB_PATH, DATA_DIR


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = Path(db_path or DB_OVERRIDE.get() or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=15)
    conn.execute("PRAGMA busy_timeout = 15000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn(db_path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS earnings_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    earnings_date TEXT NOT NULL,
    earnings_time TEXT NOT NULL DEFAULT 'Unknown',
    confirmation_status TEXT NOT NULL DEFAULT 'Unconfirmed',
    source TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(ticker, earnings_date, earnings_time)
);

CREATE TABLE IF NOT EXISTS option_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    stock_price REAL,
    strike REAL NOT NULL,
    expiration TEXT NOT NULL,
    call_bid REAL,
    call_ask REAL,
    put_bid REAL,
    put_ask REAL,
    quote_timestamp TEXT,
    call_volume INTEGER,
    put_volume INTEGER,
    call_open_interest INTEGER,
    put_open_interest INTEGER,
    source TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    category TEXT NOT NULL,
    source_url TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    strategy TEXT NOT NULL,
    strike REAL,
    expiration TEXT,
    contracts INTEGER NOT NULL DEFAULT 1,
    entry_date TEXT NOT NULL,
    entry_call_ask REAL,
    entry_put_ask REAL,
    entry_debit REAL,
    exit_date TEXT,
    exit_call_bid REAL,
    exit_put_bid REAL,
    exit_credit REAL,
    fees REAL NOT NULL DEFAULT 0,
    thesis TEXT NOT NULL DEFAULT '',
    invalidation TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    realized_pnl REAL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_earnings_date ON earnings_events(earnings_date);
CREATE INDEX IF NOT EXISTS idx_earnings_ticker ON earnings_events(ticker);
CREATE INDEX IF NOT EXISTS idx_quotes_ticker ON option_quotes(ticker);
CREATE INDEX IF NOT EXISTS idx_notes_ticker ON research_notes(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_ticker ON paper_trades(ticker);
"""


def init_db(db_path: Optional[Path] = None) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(db_path or DB_OVERRIDE.get() or DB_PATH)
    with get_conn(path) as conn:
        conn.executescript(SCHEMA_SQL)
        from earnings_radar.migrations import migrate
        migrate(conn, path)
    return path


def insert_earnings_event(conn: sqlite3.Connection, row: dict[str, Any]) -> int:
    from earnings_radar.validation import ticker, iso_date, text
    from earnings_radar.config import EARNINGS_TIMES, CONFIRMATION_STATUSES
    ticker_value = ticker(row['ticker'])
    day = iso_date(row['earnings_date'])
    now = utc_now()
    provider = text(row.get('provider'),'csv')
    identity = text(row.get('provider_event_id')) or None
    period = text(row.get('fiscal_period')) or None
    priority = {'ir':100,'exchange':90,'licensed_calendar':70}.get(provider,10)
    timing = text(row.get('earnings_time'),'Unknown')
    status = text(row.get('confirmation_status'),'Unconfirmed')
    if timing not in EARNINGS_TIMES or status not in CONFIRMATION_STATUSES:
        raise ValueError('invalid schedule timing or confirmation status')
    existing = None
    if identity:
        existing = conn.execute("SELECT * FROM earnings_events WHERE provider=? AND provider_event_id=? ORDER BY id DESC LIMIT 1", (provider,identity)).fetchone()
        if not existing:
            alias = conn.execute('SELECT event_id FROM earnings_source_evidence WHERE provider=? AND provider_event_id=? ORDER BY id DESC LIMIT 1',(provider,identity)).fetchone()
            if alias: existing=conn.execute('SELECT * FROM earnings_events WHERE id=?',(alias['event_id'],)).fetchone()
        while existing and existing['superseded_by']:
            existing=conn.execute('SELECT * FROM earnings_events WHERE id=?',(existing['superseded_by'],)).fetchone()
    if not existing and period:
        existing = conn.execute("SELECT * FROM earnings_events WHERE ticker=? AND fiscal_period=? AND superseded_by IS NULL ORDER BY id DESC LIMIT 1", (ticker_value,period)).fetchone()
    if not existing:
        existing = conn.execute("SELECT * FROM earnings_events WHERE ticker=? AND earnings_date=? AND superseded_by IS NULL ORDER BY id DESC LIMIT 1", (ticker_value,day)).fetchone()
    values = (ticker_value, day, timing, status, text(row.get('source')), now, now, provider, identity, period, row.get('feed_type','historical'),priority)
    if existing:
        # Every conflicting source stays inspectable; weak sources cannot replace stronger schedules.
        conn.execute('INSERT INTO earnings_source_evidence(event_id,provider,provider_event_id,observed_at,payload) VALUES (?,?,?,?,?)', (existing['id'],provider,identity,now,json.dumps(row)))
        same = all(existing[k] == values[i] for i,k in enumerate(['ticker','earnings_date','earnings_time','confirmation_status','source']))
        if same or priority < existing['source_priority']:
            return existing['id']
        conn.execute('INSERT INTO earnings_revisions(event_id,recorded_at,payload) VALUES (?,?,?)', (existing['id'],now,json.dumps(dict(existing))))
        exact = conn.execute('SELECT id FROM earnings_events WHERE ticker=? AND earnings_date=? AND earnings_time=?', values[:3]).fetchone()
        revision=existing['revision']+1
        if exact:
            new_id = exact['id']
            conn.execute('UPDATE earnings_events SET confirmation_status=?,source=?,updated_at=?,provider=?,provider_event_id=?,fiscal_period=?,feed_type=?,source_priority=?,revision=?,superseded_by=NULL WHERE id=?',(status,values[4],now,provider,identity,period,values[10],priority,revision,new_id))
        else:
            new_id = conn.execute("INSERT INTO earnings_events(ticker,earnings_date,earnings_time,confirmation_status,source,created_at,updated_at,provider,provider_event_id,fiscal_period,feed_type,source_priority,revision) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (*values,revision)).lastrowid
        if new_id != existing['id']:
            conn.execute('UPDATE earnings_events SET superseded_by=? WHERE id=?', (new_id,existing['id']))
        return int(new_id)
    event_id=int(conn.execute("INSERT INTO earnings_events(ticker,earnings_date,earnings_time,confirmation_status,source,created_at,updated_at,provider,provider_event_id,fiscal_period,feed_type,source_priority) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", values).lastrowid)
    conn.execute('INSERT INTO earnings_source_evidence(event_id,provider,provider_event_id,observed_at,payload) VALUES (?,?,?,?,?)',(event_id,provider,identity,now,json.dumps(row)))
    return event_id


def insert_option_quote(conn: sqlite3.Connection, row: dict[str, Any]) -> int:
    from earnings_radar.validation import validate_quote
    row = validate_quote(row)
    cur = conn.execute(
        """
        INSERT INTO option_quotes (
            ticker, stock_price, strike, expiration,
            call_bid, call_ask, put_bid, put_ask,
            quote_timestamp, call_volume, put_volume,
            call_open_interest, put_open_interest, source, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["ticker"].upper(),
            row.get("stock_price"),
            row["strike"],
            row["expiration"],
            row.get("call_bid"),
            row.get("call_ask"),
            row.get("put_bid"),
            row.get("put_ask"),
            row.get("quote_timestamp"),
            row.get("call_volume"),
            row.get("put_volume"),
            row.get("call_open_interest"),
            row.get("put_open_interest"),
            row.get("source") or "",
            utc_now(),
        ),
    )
    quote_id = int(cur.lastrowid or 0)
    conn.execute("UPDATE option_quotes SET feed_type=?,underlying_timestamp=?,call_timestamp=?,put_timestamp=?,call_contract_id=?,put_contract_id=?,multiplier=?,adjusted=? WHERE id=?", (row['feed_type'], row.get('underlying_timestamp'),row.get('call_timestamp'),row.get('put_timestamp'),row.get('call_contract_id'),row.get('put_contract_id'),row['multiplier'],int(bool(row.get('adjusted',False))),quote_id))
    return quote_id



def fetch_all(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def add_research_note(
    conn: sqlite3.Connection,
    ticker: str,
    category: str,
    source_url: str,
    notes: str,
) -> int:
    now = utc_now()
    cur = conn.execute(
        """
        INSERT INTO research_notes (ticker, category, source_url, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (ticker.upper(), category, source_url or "", notes or "", now, now),
    )
    return int(cur.lastrowid or 0)


def update_research_note(
    conn: sqlite3.Connection,
    note_id: int,
    category: str,
    source_url: str,
    notes: str,
) -> None:
    conn.execute(
        """
        UPDATE research_notes
        SET category = ?, source_url = ?, notes = ?, updated_at = ?
        WHERE id = ?
        """,
        (category, source_url or "", notes or "", utc_now(), note_id),
    )


def delete_research_note(conn: sqlite3.Connection, note_id: int) -> None:
    conn.execute("DELETE FROM research_notes WHERE id = ?", (note_id,))


def add_paper_trade(conn: sqlite3.Connection, trade: dict[str, Any]) -> int:
    from earnings_radar.paper import from_manual
    legs = from_manual(trade)
    now = utc_now()
    cur = conn.execute(
        """
        INSERT INTO paper_trades (
            ticker, strategy, strike, expiration, contracts,
            entry_date, entry_call_ask, entry_put_ask, entry_debit,
            exit_date, exit_call_bid, exit_put_bid, exit_credit,
            fees, thesis, invalidation, status, realized_pnl, notes,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            trade["ticker"].upper(),
            trade["strategy"],
            trade.get("strike"),
            trade.get("expiration"),
            trade.get("contracts", 1),
            trade["entry_date"],
            trade.get("entry_call_ask"),
            trade.get("entry_put_ask"),
            trade.get("entry_debit"),
            trade.get("exit_date"),
            trade.get("exit_call_bid"),
            trade.get("exit_put_bid"),
            trade.get("exit_credit"),
            trade.get("fees", 0) or 0,
            trade.get("thesis") or "",
            trade.get("invalidation") or "",
            trade.get("status") or "open",
            trade.get("realized_pnl"),
            trade.get("notes") or "",
            now,
            now,
        ),
    )
    trade_id = int(cur.lastrowid or 0)
    for leg in legs:
        conn.execute('INSERT INTO paper_legs(trade_id,side,quantity,strike,expiration,option_type,multiplier,contract_id,premium) VALUES (?,?,?,?,?,?,?,?,?)', (trade_id,leg['side'],leg['quantity'],leg['strike'],leg['expiration'],leg['option_type'],leg['multiplier'],leg.get('contract_id'),leg['premium']))
    conn.execute('UPDATE paper_trades SET evaluation_id=?,origin=? WHERE id=?', (trade.get('evaluation_id'),trade.get('origin','manual_simulation'),trade_id))
    return trade_id



def close_paper_trade(
    conn: sqlite3.Connection,
    trade_id: int,
    exit_date: str,
    exit_call_bid: Optional[float],
    exit_put_bid: Optional[float],
    exit_credit: float,
    fees: float,
    realized_pnl: float,
    notes: str = "",
) -> None:
    conn.execute(
        """
        UPDATE paper_trades
        SET exit_date = ?, exit_call_bid = ?, exit_put_bid = ?, exit_credit = ?,
            fees = ?, realized_pnl = ?, status = 'closed', notes = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            exit_date,
            exit_call_bid,
            exit_put_bid,
            exit_credit,
            fees,
            realized_pnl,
            notes,
            utc_now(),
            trade_id,
        ),
    )


def clear_table(conn: sqlite3.Connection, table: str) -> None:
    allowed = {
        "earnings_events",
        "option_quotes",
        "research_notes",
        "paper_trades",
    }
    if table not in allowed:
        raise ValueError(f"Refusing to clear unknown table: {table}")
    conn.execute(f"DELETE FROM {table}")
