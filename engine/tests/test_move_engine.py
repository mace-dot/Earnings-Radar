from datetime import datetime, timedelta, timezone
import re
import pytest
from engine.lines import build_lines
from engine.move_features import event_volatility, setup_features
from engine.options_estimates import chain_estimate
from engine.providers.base import Observation
from engine.sectors import sector_for_sic

NOW = datetime(2026, 10, 7, 19, tzinfo=timezone.utc)


def test_sic_specific_sectors_precede_broad_ranges():
    assert sector_for_sic("3674")[0] == "Information Technology"
    assert sector_for_sic("1311")[0] == "Energy"
    assert sector_for_sic("2834")[0] == "Health Care"


def test_event_variance_hand_calculation():
    assert event_volatility(0.6, 0.1, 0.5, 0.2) == pytest.approx((0.036 - 0.014) ** 0.5)
    with pytest.raises(ValueError):
        event_volatility(0.1, 0.2, 0.6, 0.1)


def test_each_side_has_distinct_numbered_evidence():
    feature = {
        "sample_size": 290,
        "last_close": 100,
        "atr_14": 2,
        "return_20": 0.1,
        "sma_50_distance": 0.02,
        "dist_52w_high": -0.05,
        "rv_10": 0.3,
        "vol_compression_ratio": 0.6,
        "bb_width_percentile": 0.2,
    }
    lines, sides = build_lines("TEST", feature, NOW)
    assert len(lines) == 6
    for line in lines:
        pair = [s for s in sides if s["line_id"] == line["id"]]
        assert pair[0]["payload"]["bullets"] != pair[1]["payload"]["bullets"]
        assert all(
            re.search(r"\d", bullet) for s in pair for bullet in s["payload"]["bullets"]
        )


def test_indicative_straddle_is_estimate_not_executable():
    snapshots = [
        {
            "contract_id": f"TEST261023{kind}00100000",
            "latestQuote": {"bp": 2, "ap": 2.2, "t": NOW.isoformat()},
        }
        for kind in ("C", "P")
    ]
    result = chain_estimate("TEST", 100, snapshots, NOW, "2026-10-20")
    assert result["implied_move"] == pytest.approx(0.042)
    assert result["executable"] is False
    assert result["upper_breakeven"] == pytest.approx(104.2)
    assert result["event_specific"] is True


def test_move_features_reject_future_data():
    with pytest.raises(ValueError):
        setup_features(
            [
                Observation(
                    "TEST", NOW, NOW + timedelta(seconds=1), "fixture", {"c": 100}
                )
            ],
            NOW,
        )


def test_unscored_symbol_completes_one_queue_cycle(monkeypatch):
    from engine import run
    from engine import research

    class FakeStore:
        def __init__(self):
            self.finished = []

        def rpc(self, name, payload):
            assert name == "radar_claim_scores"
            return [{"symbol": "TEST"}]

        def read(self, table, params):
            return (
                [{"symbol": "TEST", "sector": "Information Technology"}]
                if table == "securities"
                else []
            )

        def write(self, *args, **kwargs):
            pass

        def finish_score(self, symbol, reason=None):
            self.finished.append((symbol, reason))

    store = FakeStore()
    monkeypatch.setattr(run, "enrich", lambda security: security)
    monkeypatch.setattr(run, "prices", lambda *args: {})
    monkeypatch.setattr(run, "score", lambda *args: {})
    monkeypatch.setattr(research, "market_context", lambda *args: {})
    monkeypatch.setattr(research, "news_context", lambda *args: {})
    assert run.drain_queue(store) == {"claimed": 1, "completed": 1}
    assert store.finished == [("TEST", None)]


def test_unavailable_price_feed_has_cases_without_made_up_values():
    lines, sides = build_lines("TEST", {"sample_size": 0, "feed": None}, NOW)
    assert len(lines) == 6
    assert all(s["payload"]["trade"]["entry"] is None for s in sides)
    assert all("Price history missing" in s["payload"]["badges"] for s in sides)


def test_magnitude_training_cannot_promote_with_insufficient_data():
    from engine.models import magnitude_challenger

    result = magnitude_challenger([[1], [2]], [0.02, 0.03], [0.01, 0.01], [2019, 2020])
    assert result["status"] == "challenger"
    assert result["out_of_sample_n"] == 0


def test_magnitude_calibration_precedes_test_year_and_remains_challenger():
    from engine.models import magnitude_challenger
    from threadpoolctl import threadpool_limits

    x = [[float(i % 2), float(i % 7)] for i in range(400)]
    moves = [0.03 if i % 2 else 0.01 for i in range(400)]
    years = [2016] * 180 + [2017] * 100 + [2018] * 120
    with threadpool_limits(limits=2):
        report = magnitude_challenger(x, moves, [0.02] * 400, years)
    assert report["status"] == "challenger"
    assert report["out_of_sample_n"] == 120
    assert (
        report["folds"][0]["train_end_year"]
        < report["folds"][0]["calibration_year"]
        < report["folds"][0]["test_year"]
    )
    assert all(q["p80"] >= q["median"] >= 0 for q in report["quantiles"])


def test_magnitude_is_not_graded_as_bear_direction():
    from engine.grading import grade_direction, grade_magnitude

    pick = {
        "id": "fixture",
        "side": "MORE",
        "expires_at": NOW.isoformat(),
        "payload": {"entry": 100, "implied_move": 0.05},
    }
    with pytest.raises(ValueError):
        grade_direction(pick, 110, NOW, "fixture")
    assert grade_magnitude(pick, 110, NOW, "fixture")["payload"]["result"] == "win"


def test_future_indicative_leg_rejected():
    snapshots = [
        {
            "contract_id": f"TEST261023{kind}00100000",
            "latestQuote": {
                "bp": 2,
                "ap": 2.2,
                "t": (NOW + timedelta(seconds=1)).isoformat(),
            },
        }
        for kind in ("C", "P")
    ]
    with pytest.raises(ValueError, match="cutoff"):
        chain_estimate("TEST", 100, snapshots, NOW)
