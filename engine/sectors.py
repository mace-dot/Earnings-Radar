"""Explicit SIC-derived classification; unknown is not assigned a made-up sector."""

from typing import Any
from datetime import datetime, timezone

from engine.providers.sec import SEC


def sector_for_sic(sic: str) -> tuple[str, str | None]:
    code = int(sic) if sic.isdigit() else -1
    if 1300 <= code <= 1399 or 2900 <= code <= 2999:
        return "Energy", "XLE"
    if 2830 <= code <= 2836 or 8000 <= code <= 8099 or 3840 <= code <= 3851:
        return "Health Care", "XLV"
    if 1000 <= code <= 1499 or 2800 <= code <= 2899:
        return "Materials", "XLB"
    if 3570 <= code <= 3579 or 3660 <= code <= 3699 or 7370 <= code <= 7379:
        return "Information Technology", "XLK"
    if 4800 <= code <= 4899 or 7810 <= code <= 7841:
        return "Communication Services", "XLC"
    if 4900 <= code <= 4999:
        return "Utilities", "XLU"
    if 6500 <= code <= 6599 or code == 6798:
        return "Real Estate", "XLRE"
    if 6000 <= code <= 6999:
        return "Financials", "XLF"
    if 2000 <= code <= 2199 or 5400 <= code <= 5499:
        return "Consumer Staples", "XLP"
    if (
        2300 <= code <= 2599
        or 3700 <= code <= 3799
        or 5000 <= code <= 5999
        or 7000 <= code <= 7299
    ):
        return "Consumer Discretionary", "XLY"
    if (
        1500 <= code <= 1799
        or 3000 <= code <= 3999
        or 4000 <= code <= 4799
        or 7300 <= code <= 8999
    ):
        return "Industrials", "XLI"
    return "Classification unavailable", None


def enrich(security: dict[str, Any]) -> dict[str, Any]:
    cik = security.get("cik", "")
    if len(cik) != 10 or not cik.isdigit():
        return security
    client = SEC().client
    response = client.get(f"https://data.sec.gov/submissions/CIK{cik}.json")
    response.raise_for_status()
    data = response.json()
    sector, etf = sector_for_sic(str(data.get("sic", "")))
    return {
        **security,
        "sector": sector,
        "sector_etf": etf,
        "industry": data.get("sicDescription"),
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source": f"https://data.sec.gov/submissions/CIK{cik}.json",
    }
