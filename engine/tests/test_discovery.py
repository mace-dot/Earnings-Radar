from datetime import datetime, timezone, timedelta

from engine.discovery import select_candidates

NOW = datetime(2026, 10, 8, 14, tzinfo=timezone.utc)


def rows():
    features = [
        {
            "symbol": f"TEST{i}",
            "as_of": NOW.isoformat(),
            "values": {
                "source_last_observed_at": NOW.isoformat(),
                "sample_size": 80,
                "last_close": 100,
                "adv_20": 10_000_000,
                "vol_compression_ratio": 0.5 + i / 20,
                "return_20": i / 100,
            },
        }
        for i in range(20)
    ]
    securities = [
        {
            "symbol": row["symbol"],
            "asset_type": "common_stock",
            "listing_metadata": {"retrieved_at": NOW.isoformat()},
        }
        for row in features
    ]
    return features, securities


def test_priority_combines_quietness_trend_and_fair_review_without_probability():
    features, securities = rows()
    selected = select_candidates(features, securities, {}, NOW)
    assert len(selected) == 10
    assert len({row["symbol"] for row in selected}) == 10
    assert selected[0]["symbol"] == "TEST0"
    assert "TEST19" in {row["symbol"] for row in selected}
    assert all("probability" not in row for row in selected)


def test_missing_liquidity_unverified_identity_future_and_recent_review_are_excluded():
    features, securities = rows()
    features[0]["values"]["adv_20"] = None
    securities[1]["asset_type"] = "warrant"
    features[2]["as_of"] = (NOW + timedelta(seconds=1)).isoformat()
    selected = select_candidates(features, securities, {"TEST3": NOW.isoformat()}, NOW)
    assert not {"TEST0", "TEST1", "TEST2", "TEST3"} & {
        row["symbol"] for row in selected
    }
