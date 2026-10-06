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


def _optional_float(value: Any) -> Optional[float]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return float(value)


def _optional_int(value: Any) -> Optional[int]:
    f = _optional_float(value)
    return None if f is None else int(f)


def validate_earnings_df(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    errors: list[str] = []
    df = _normalize_columns(df)
    missing = [c for c in EARNINGS_COLUMNS if c not in df.columns]
    if missing:
        return df, [f"Missing required columns: {', '.join(missing)}"]

    cleaned_rows: list[dict[str, Any]] = []
    for i, row in df.iterrows():
        line = int(i) + 2  # header + 1-based
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            errors.append(f"Row {line}: ticker is required")
            continue
        earnings_date = str(row.get("earnings_date") or "").strip()
        if not earnings_date:
            errors.append(f"Row {line}: earnings_date is required")
            continue
        earnings_time = str(row.get("earnings_time") or "Unknown").strip() or "Unknown"
        if earnings_time not in EARNINGS_TIMES:
            errors.append(
                f"Row {line}: earnings_time must be one of {', '.join(EARNINGS_TIMES)}"
            )
            continue
        status = str(row.get("confirmation_status") or "Unconfirmed").strip() or "Unconfirmed"
        if status not in CONFIRMATION_STATUSES:
            errors.append(
                f"Row {line}: confirmation_status must be one of "
                f"{', '.join(CONFIRMATION_STATUSES)}"
            )
            continue
        cleaned_rows.append(
            {
                "ticker": ticker,
                "earnings_date": earnings_date[:10],
                "earnings_time": earnings_time,
                "confirmation_status": status,
                "source": str(row.get("source") or "").strip(),
            }
        )
    return pd.DataFrame(cleaned_rows), errors


def validate_options_df(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    errors: list[str] = []
    df = _normalize_columns(df)
    missing = [c for c in ("ticker", "strike", "expiration") if c not in df.columns]
    if missing:
        return df, [f"Missing required columns: {', '.join(missing)}"]

    for col in OPTION_COLUMNS:
        if col not in df.columns:
            df[col] = None

    cleaned_rows: list[dict[str, Any]] = []
    for i, row in df.iterrows():
        line = int(i) + 2
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker:
            errors.append(f"Row {line}: ticker is required")
            continue
        try:
            strike = _optional_float(row.get("strike"))
        except (TypeError, ValueError):
            errors.append(f"Row {line}: strike must be numeric")
            continue
        if strike is None:
            errors.append(f"Row {line}: strike is required")
            continue
        expiration = str(row.get("expiration") or "").strip()
        if not expiration:
            errors.append(f"Row {line}: expiration is required")
            continue
        try:
            cleaned_rows.append(
                {
                    "ticker": ticker,
                    "stock_price": _optional_float(row.get("stock_price")),
                    "strike": strike,
                    "expiration": expiration[:10],
                    "call_bid": _optional_float(row.get("call_bid")),
                    "call_ask": _optional_float(row.get("call_ask")),
                    "put_bid": _optional_float(row.get("put_bid")),
                    "put_ask": _optional_float(row.get("put_ask")),
                    "quote_timestamp": (
                        None
                        if row.get("quote_timestamp") is None
                        or (isinstance(row.get("quote_timestamp"), float) and pd.isna(row.get("quote_timestamp")))
                        else str(row.get("quote_timestamp")).strip()
                    ),
                    "call_volume": _optional_int(row.get("call_volume")),
                    "put_volume": _optional_int(row.get("put_volume")),
                    "call_open_interest": _optional_int(row.get("call_open_interest")),
                    "put_open_interest": _optional_int(row.get("put_open_interest")),
                    "source": str(row.get("source") or "").strip(),
                }
            )
        except (TypeError, ValueError) as exc:
            errors.append(f"Row {line}: invalid numeric field ({exc})")
    return pd.DataFrame(cleaned_rows), errors


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


def load_sample_data(*, replace: bool = True) -> dict[str, Any]:
    """Load clearly labeled sample CSVs into the local DB."""
    earn_path = SAMPLES_DIR / "sample_earnings_calendar.csv"
    opt_path = SAMPLES_DIR / "sample_option_chains.csv"
    if not earn_path.exists() or not opt_path.exists():
        return {
            "ok": False,
            "errors": [f"Sample files missing under {SAMPLES_DIR}"],
        }
    e = import_earnings_csv(earn_path, replace=replace)
    o = import_options_csv(opt_path, replace=replace)
    return {
        "ok": e["ok"] and o["ok"],
        "earnings_imported": e.get("imported", 0),
        "options_imported": o.get("imported", 0),
        "errors": e.get("errors", []) + o.get("errors", []),
    }


def read_template_bytes(name: str) -> bytes:
    path = TEMPLATES_DIR / name
    return path.read_bytes()


def read_sample_bytes(name: str) -> bytes:
    path = SAMPLES_DIR / name
    return path.read_bytes()
