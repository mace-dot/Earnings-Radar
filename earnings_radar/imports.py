"""CSV import, templates, and sample-data helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import pandas as pd

from earnings_radar.config import CONFIRMATION_STATUSES, EARNINGS_TIMES, SAMPLES_DIR, TEMPLATES_DIR
from earnings_radar.db import get_conn, init_db, insert_earnings_event, insert_option_quote

EARNINGS_COLUMNS = [
    "ticker",
    "earnings_date",
    "earnings_time",
    "confirmation_status",
    "source",
]

OPTION_COLUMNS = [
    "ticker",
    "stock_price",
    "strike",
    "expiration",
    "call_bid",
    "call_ask",
    "put_bid",
    "put_ask",
    "quote_timestamp",
    "call_volume",
    "put_volume",
    "call_open_interest",
    "put_open_interest",
    "source",
]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip().lower().replace(" ", "_") for c in out.columns]
    return out


from earnings_radar.validation import text, ticker, iso_date, validate_quote


def validate_earnings_df(df):
    df = _normalize_columns(df)
    missing = [c for c in EARNINGS_COLUMNS if c not in df.columns]
    if missing:
        return df, [f"Missing required columns: {', '.join(missing)}"]
    cleaned, errors = [], []
    for line, (_, row) in enumerate(df.iterrows(), 2):
        try:
            time = text(row.get('earnings_time'), 'Unknown')
            status = text(row.get('confirmation_status'), 'Unconfirmed')
            if time not in EARNINGS_TIMES:
                raise ValueError('invalid earnings_time')
            if status not in CONFIRMATION_STATUSES:
                raise ValueError('invalid confirmation_status')
            cleaned.append(dict(ticker=ticker(row.get('ticker')), earnings_date=iso_date(row.get('earnings_date')), earnings_time=time, confirmation_status=status, source=text(row.get('source')), provider=text(row.get('provider'),'csv'),provider_event_id=text(row.get('provider_event_id')) or None,fiscal_period=text(row.get('fiscal_period')) or None,feed_type=text(row.get('feed_type'),'historical')))
        except (TypeError, ValueError) as exc:
            errors.append(f'Row {line}: {exc}')
    return pd.DataFrame(cleaned, dtype=object), errors


def validate_options_df(df):
    df = _normalize_columns(df)
    missing = [c for c in ('ticker','strike','expiration') if c not in df.columns]
    if missing:
        return df, [f"Missing required columns: {', '.join(missing)}"]
    cleaned, errors = [], []
    for line, (_, row) in enumerate(df.iterrows(), 2):
        try:
            cleaned.append(validate_quote(row.to_dict()))
        except (TypeError, ValueError) as exc:
            errors.append(f'Row {line}: {exc}')
    return pd.DataFrame(cleaned, dtype=object), errors


def import_earnings_csv(path_or_buffer, *, replace: bool = False) -> dict[str, Any]:
    init_db()
    df = pd.read_csv(path_or_buffer)
    cleaned, errors = validate_earnings_df(df)
    if errors:
        return {"ok": False, "imported": 0, "errors": errors}
    with get_conn() as conn:
        if replace:
            conn.execute("DELETE FROM earnings_events")
        for _, row in cleaned.iterrows():
            insert_earnings_event(conn, row.to_dict())
    return {"ok": True, "imported": len(cleaned), "errors": []}


def import_options_csv(path_or_buffer, *, replace: bool = False) -> dict[str, Any]:
    init_db()
    df = pd.read_csv(path_or_buffer)
    cleaned, errors = validate_options_df(df)
    if errors:
        return {"ok": False, "imported": 0, "errors": errors}
    with get_conn() as conn:
        if replace:
            conn.execute("DELETE FROM option_quotes")
        for _, row in cleaned.iterrows():
            insert_option_quote(conn, row.to_dict())
    return {"ok": True, "imported": len(cleaned), "errors": []}


def load_sample_data(*, replace: bool = True, db_path=None):
    """Samples live exclusively in a separate demo DB; never clear the real DB."""
    from earnings_radar.config import DATA_DIR
    from earnings_radar.validation import validate_quote
    path = Path(db_path or DATA_DIR / 'demo.db')
    import earnings_radar.db as db
    if path.resolve() == Path(db.DB_PATH).resolve():
        raise ValueError('sample database must differ from the real database')
    init_db(path)
    e, errors = validate_earnings_df(pd.read_csv(SAMPLES_DIR / 'sample_earnings_calendar.csv'))
    # Sample timestamps deliberately describe a fictional historical snapshot.
    o = pd.read_csv(SAMPLES_DIR / 'sample_option_chains.csv')
    if errors:
        return {'ok':False,'errors':errors}
    with get_conn(path) as conn:
        if replace:
            conn.execute('DELETE FROM earnings_revisions')
            conn.execute('UPDATE earnings_events SET superseded_by=NULL')
            conn.execute('DELETE FROM earnings_events')
            conn.execute('DELETE FROM option_quotes')
        for _, row in e.iterrows():
            insert_earnings_event(conn, {**row.to_dict(),'feed_type':'sample'})
        for _, row in o.iterrows():
            insert_option_quote(conn, {**row.to_dict(),'feed_type':'sample'})
    return {'ok':True,'earnings_imported':len(e),'options_imported':len(o),'errors':[], 'db_path':str(path)}


def read_template_bytes(name: str) -> bytes:
    path = TEMPLATES_DIR / name
    return path.read_bytes()


def read_sample_bytes(name: str) -> bytes:
    path = SAMPLES_DIR / name
    return path.read_bytes()
