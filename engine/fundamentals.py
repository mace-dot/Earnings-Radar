"""Comparable SEC quarters and balance-sheet periods, with filing provenance."""

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

TAGS = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "cash": ("CashAndCashEquivalentsAtCarryingValue",),
    "current_assets": ("AssetsCurrent",),
    "current_liabilities": ("LiabilitiesCurrent",),
}


def observations(
    facts: dict[str, Any], metric: str, cutoff: datetime
) -> list[dict[str, Any]]:
    filing_cutoff = cutoff.astimezone(ZoneInfo("America/New_York")).date()
    output = []
    for tag in TAGS[metric]:
        rows = (
            facts.get("facts", {})
            .get("us-gaap", {})
            .get(tag, {})
            .get("units", {})
            .get("USD", [])
        )
        for row in rows:
            if (
                row.get("form") not in {"10-Q", "10-K", "10-Q/A", "10-K/A"}
                or not row.get("filed")
                or not row.get("end")
            ):
                continue
            if (
                date.fromisoformat(row["filed"]) > filing_cutoff
                or date.fromisoformat(row["end"]) > cutoff.date()
            ):
                continue
            if metric in {"revenue", "net_income"}:
                if (
                    not row.get("start")
                    or not 70
                    <= (
                        date.fromisoformat(row["end"])
                        - date.fromisoformat(row["start"])
                    ).days
                    <= 110
                ):
                    continue
            output.append({**row, "tag": tag, "unit": "USD"})
        if output:
            break
    # Select the latest available amendment for each period; do not count repeated filings as separate quarters.
    by_period = {}
    for row in sorted(output, key=lambda r: r["filed"]):
        by_period[(row.get("start"), row["end"])] = row
    return sorted(by_period.values(), key=lambda r: r["end"], reverse=True)


def extract(facts: dict[str, Any], cutoff: datetime) -> dict[str, Any]:
    rows = {metric: observations(facts, metric, cutoff) for metric in TAGS}
    revenue = rows["revenue"][0] if rows["revenue"] else None
    prior = next(
        (
            r
            for r in rows["revenue"][1:]
            if revenue
            and 350
            <= (date.fromisoformat(revenue["end"]) - date.fromisoformat(r["end"])).days
            <= 380
            and abs(
                (
                    date.fromisoformat(revenue["end"])
                    - date.fromisoformat(revenue["start"])
                ).days
                - (date.fromisoformat(r["end"]) - date.fromisoformat(r["start"])).days
            )
            <= 10
        ),
        None,
    )
    income = next(
        (
            r
            for r in rows["net_income"]
            if revenue and r["start"] == revenue["start"] and r["end"] == revenue["end"]
        ),
        None,
    )
    assets = rows["current_assets"][0] if rows["current_assets"] else None
    liabilities = next(
        (
            r
            for r in rows["current_liabilities"]
            if assets and r["end"] == assets["end"]
        ),
        None,
    )
    cash = rows["cash"][0] if rows["cash"] else None
    values = {
        "quarter_revenue_yoy": (
            revenue["val"] / prior["val"] - 1
            if revenue and prior and prior["val"] > 0
            else None
        ),
        "quarter_net_margin": (
            income["val"] / revenue["val"] if income and revenue["val"] > 0 else None
        ),
        "current_ratio": (
            assets["val"] / liabilities["val"]
            if assets and liabilities and liabilities["val"] > 0
            else None
        ),
        "cash": cash["val"] if cash else None,
    }
    cik = str(facts.get("cik", ""))
    provenance = {
        "revenue": revenue,
        "prior_revenue": prior,
        "income": income,
        "assets": assets,
        "liabilities": liabilities,
        "cash": cash,
    }
    for row in provenance.values():
        if row and row.get("accn") and cik.isdigit():
            row["filing_url"] = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{row['accn'].replace('-', '')}/{row['accn']}-index.html"
            )
    return {
        "values": values,
        "periods": provenance,
        "source": "SEC company facts",
        "retrieved_at": cutoff.isoformat(),
        "filing_time_precision": "date only; retrieval time is separate",
        "missing": [k for k, v in values.items() if v is None],
    }
