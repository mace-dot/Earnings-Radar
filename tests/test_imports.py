"""CSV import smoke tests against an isolated temp database."""

from __future__ import annotations

from pathlib import Path

import earnings_radar.config as config
import earnings_radar.db as db
from earnings_radar.imports import import_earnings_csv, import_options_csv, load_sample_data


def test_sample_import(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(db, "DB_PATH", db_path)

    result = load_sample_data(replace=True)
    assert result["ok"] is True
    assert result["earnings_imported"] == 4
    assert result["options_imported"] == 6

    with db.get_conn(db_path) as conn:
        n_e = conn.execute("SELECT COUNT(*) AS n FROM earnings_events").fetchone()["n"]
        n_o = conn.execute("SELECT COUNT(*) AS n FROM option_quotes").fetchone()["n"]
    assert n_e == 4
    assert n_o == 6


def test_reject_bad_confirmation(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "bad.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(db, "DB_PATH", db_path)

    csv = "ticker,earnings_date,earnings_time,confirmation_status,source\nAAA,2026-10-15,AMC,Maybe,x\n"
    path = tmp_path / "bad.csv"
    path.write_text(csv, encoding="utf-8")
    result = import_earnings_csv(path)
    assert result["ok"] is False
    assert any("confirmation_status" in e for e in result["errors"])
