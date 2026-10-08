from datetime import datetime, timezone

from engine.fundamentals import extract

NOW = datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc)


def test_matched_quarters_and_future_filing_guard():
    rows = [
        {"start": start, "end": end, "filed": filed, "val": val, "form": "10-Q"}
        for start, end, filed, val in [
            ("2026-04-01", "2026-06-30", "2026-08-01", 120),
            ("2025-04-01", "2025-06-30", "2025-08-01", 100),
            ("2026-01-01", "2026-06-30", "2026-08-01", 300),
            ("2026-07-01", "2026-09-30", "2026-10-08", 999),
        ]
    ]
    result = extract(
        {"facts": {"us-gaap": {"Revenues": {"units": {"USD": rows}}}}}, NOW
    )
    assert round(result["values"]["quarter_revenue_yoy"], 2) == 0.2
    assert result["periods"]["revenue"]["end"] == "2026-06-30"
    assert result["values"]["quarter_net_margin"] is None


def test_balance_sheet_dates_must_match():
    def fact(end, val):
        return {
            "units": {
                "USD": [{"end": end, "filed": "2026-08-01", "form": "10-Q", "val": val}]
            }
        }

    result = extract(
        {
            "facts": {
                "us-gaap": {
                    "AssetsCurrent": fact("2026-06-30", 100),
                    "LiabilitiesCurrent": fact("2026-03-31", 50),
                }
            }
        },
        NOW,
    )
    assert result["values"]["current_ratio"] is None
