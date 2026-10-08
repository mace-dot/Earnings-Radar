"""Official exchange directories; conservative security-name classification."""

import csv
import io
from datetime import datetime, timezone
from typing import Any

import httpx

SOURCES = (
    "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
)


def classify(row: dict[str, str]) -> str:
    name = row.get("Security Name", "").lower()
    if row.get("Test Issue") != "N":
        return "test_issue"
    if row.get("ETF") == "Y":
        return "fund"
    for term, kind in (
        ("warrant", "warrant"),
        ("preferred", "preferred"),
        ("depositary", "depositary_security"),
        ("units", "unit"),
        (" notes", "debt_security"),
    ):
        if term in name:
            return kind
    if any(
        term in name
        for term in (
            "common stock",
            "common shares",
            "capital stock",
            "ordinary shares",
        )
    ):
        return "common_stock"
    return "listed_unclassified"


def directory() -> dict[str, dict[str, Any]]:
    output = {}
    with httpx.Client(timeout=30) as client:
        for url in SOURCES:
            response = client.get(url)
            response.raise_for_status()
            text = response.text
            if "Security Name" not in text.splitlines()[0]:
                raise ValueError("Unexpected exchange directory format")
            rows = list(csv.DictReader(io.StringIO(text), delimiter="|"))
            if len(rows) < 1000:
                raise ValueError("Unexpectedly small exchange directory")
            retrieved = datetime.now(timezone.utc).isoformat()
            for row in rows:
                symbol = row.get("Symbol") or row.get("ACT Symbol")
                if not symbol or symbol.startswith("File Creation"):
                    continue
                output[symbol] = {
                    "asset_type": classify(row),
                    "listing_metadata": {
                        "source": url,
                        "retrieved_at": retrieved,
                        "security_name": row.get("Security Name"),
                        "etf": row.get("ETF"),
                        "test_issue": row.get("Test Issue"),
                        "classification_rule": "exchange-directory-name-v1; not prospectus verification",
                    },
                }
    return output
