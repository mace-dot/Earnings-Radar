from datetime import datetime, timedelta, timezone

import pytest

from engine.calendar import reconcile
from engine.features import implied_move, price_features
from engine.lines import build_lines, exposure
from engine.models import eligible_probability, walk_forward
from engine.providers.base import Observation

NOW = datetime(2026, 10, 7, tzinfo=timezone.utc)


def test_future_observation_fails():
    bar = Observation("TEST", NOW, NOW + timedelta(seconds=1), "fixture", {"c": 100})
    with pytest.raises(ValueError, match="cutoff"):
        price_features([bar], NOW)


def test_prices_and_volatility():
    bars = [
        Observation(
            "TEST",
            NOW - timedelta(days=30 - i),
            NOW,
            "fixture",
            {"c": 100 + i, "h": 102 + i, "l": 99 + i, "v": 1000},
        )
        for i in range(30)
    ]
    features = price_features(bars, NOW)
    assert features["return_20"] == pytest.approx(129 / 109 - 1)
    assert features["atr_14"] == 3
    assert features["realized_volatility_20"] > 0


@pytest.mark.parametrize(
    "spot,cb,ca,pb,pa,expected",
    [
        (100 + i * 10, 2 + i, 3 + i, 1 + i, 2 + i, (4 + 2 * i) / (100 + i * 10))
        for i in range(10)
    ],
)
def test_hand_calculated_implied_moves(spot, cb, ca, pb, pa, expected):
    assert abs(implied_move(spot, cb, ca, pb, pa) - expected) < 0.001


def test_crossed_quote_rejected():
    with pytest.raises(ValueError):
        implied_move(100, 4, 3, 1, 2)


def test_calendar_conflict_not_confirmed():
    observations = [
        Observation("TEST", NOW, NOW, source, {"date": date})
        for source, date in [("fixture A", "2026-10-20"), ("fixture B", "2026-10-21")]
    ]
    assert reconcile(observations, NOW)[0]["date_status"] == "conflicting"


def test_missing_options_only_affect_their_setup():
    lines, sides = build_lines(
        "TEST", {"last_close": 100, "atr_14": 2, "return_20": 0.1}, NOW
    )
    assert len(lines) == 5
    swing = next(
        s
        for s in sides
        if s["line_id"].split(":")[1] == "Swing" and s["side"] == "BULL"
    )
    assert swing["payload"]["trade"]["stop"] == 97
    assert swing["payload"]["trade"]["missing"] == []
    assert all(s["payload"]["probability"] is None for s in sides)
    assert all(len(s["payload"]["bullets"]) == 3 for s in sides)


def test_budget_unknown_is_not_empty():
    assert exposure(2, 100)["quantity"] is None
    assert exposure(2, 100, 20000)["quantity"] == 1


def test_sample_size_alone_cannot_enable_probability():
    assert not eligible_probability(
        {"status": "validated", "out_of_sample_n": 500}, "Swing", "60", "US"
    )


def test_walk_forward_uses_prior_years_only():
    x = [[i % 13, i % 7] for i in range(300)]
    result = walk_forward(
        x, [i % 2 for i in range(300)], [2019 + i // 100 for i in range(300)]
    )
    assert result["out_of_sample_n"] == 200
    assert result["status"] == "challenger"
    assert all(f["train_end_year"] < f["test_year"] for f in result["folds"])
    assert sum(bucket["n"] for bucket in result["reliability"]) == 200


def test_indicative_options_never_become_executable_trade():
    from engine.options import Contract, select_long

    item = Contract(
        "TEST261120C00100000",
        "call",
        100,
        NOW + timedelta(days=30),
        2,
        2.1,
        0.5,
        100,
        NOW,
        "indicative",
        1000,
    )
    result = select_long([item], "BULL", NOW)
    assert result["contract"] is None
    assert "non_executable_feed" in result["missing_reasons"]


def test_long_option_max_loss_uses_ask_and_multiplier():
    from engine.options import Contract, select_long

    item = Contract(
        "TEST261120P00100000",
        "put",
        100,
        NOW + timedelta(days=30),
        2,
        2.1,
        -0.5,
        100,
        NOW,
        "opra",
        1000,
    )
    assert select_long([item], "BEAR", NOW)["one_contract_max_loss"] == 210


def test_daily_provider_excludes_still_forming_sessions():
    import httpx
    from engine.providers.market import Alpaca

    provider = Alpaca()
    provider.client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "bars": {
                        "TEST": [
                            {"t": "2099-01-01T05:00:00Z", "c": 100},
                            {"t": "2020-01-02T05:00:00Z", "c": 90},
                        ]
                    },
                    "next_page_token": None,
                },
            )
        )
    )
    bars = provider.bars(["TEST"], "2020-01-01", "2099-01-02")
    assert len(bars) == 1
    assert bars[0].values["c"] == 90
    assert bars[0].observed_at.hour == 21


def test_schedule_uses_eastern_dst():
    from engine.schedule import due_jobs

    assert due_jobs(datetime(2026, 10, 7, 10, 0, tzinfo=timezone.utc)) == ["universe"]
    assert due_jobs(datetime(2026, 12, 7, 11, 0, tzinfo=timezone.utc)) == ["universe"]
    assert due_jobs(datetime(2026, 12, 7, 10, 0, tzinfo=timezone.utc)) == []


def test_direction_grading_waits_for_horizon_and_does_not_claim_option_pnl():
    from engine.grading import grade_direction

    pick = {
        "id": "fixture",
        "side": "BEAR",
        "expires_at": (NOW + timedelta(days=1)).isoformat(),
        "payload": {"entry": 100},
    }
    with pytest.raises(ValueError, match="horizon"):
        grade_direction(pick, 90, NOW, "fixture")
    result = grade_direction(pick, 90, NOW + timedelta(days=2), "fixture")
    assert result["payload"]["return_fraction"] == pytest.approx(0.1)
    assert result["payload"]["contract_pnl"] is None
