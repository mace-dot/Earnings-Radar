"""App configuration. API keys stay in .env (gitignored), not here."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
TEMPLATES_DIR = DATA_DIR / "templates"
SAMPLES_DIR = DATA_DIR / "samples"
EXPORTS_DIR = ROOT_DIR / "exports"

DB_PATH = Path(os.getenv("EARNINGS_RADAR_DB_PATH", DATA_DIR / "earnings_radar.db"))

# Quote older than this many hours is flagged stale (liquidity).
STALE_QUOTE_HOURS = float(os.getenv("STALE_QUOTE_HOURS", "24"))

# Mid-based spread % above this is flagged wide (liquidity).
WIDE_SPREAD_PCT = float(os.getenv("WIDE_SPREAD_PCT", "15"))

# Minimum volume / OI hints for liquidity flags (not hard blocks).
LOW_VOLUME = int(os.getenv("LOW_VOLUME", "10"))
LOW_OPEN_INTEREST = int(os.getenv("LOW_OPEN_INTEREST", "50"))

RESEARCH_NOTE_CATEGORIES = (
    "guidance",
    "peers",
    "customers",
    "margins",
    "contradictory_evidence",
    "other",
)

CONFIRMATION_STATUSES = ("Confirmed", "Estimated", "Unconfirmed")
EARNINGS_TIMES = ("BMO", "AMC", "During Market", "Unknown")
