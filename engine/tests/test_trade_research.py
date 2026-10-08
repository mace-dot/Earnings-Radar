from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from engine.lines import build_lines
from engine.trade_research import expiration_outcome, long_options, paper_pick

NOW = datetime(2026, 10, 8, 14, tzinfo=timezone.utc)


def quote(kind="C", bid=2, ask=2.2, delta=0.5):
    return {
        "contract_id": f"TEST261106{kind}00100000",
        "latestQuote": {"bp": bid, "ap": ask, "t": NOW.isoformat()},
        "greeks": {"delta": delta},
    }


def make_pick(side="BULL"):
    feature = {
        "sample_size": 100,
        "last_close": 100,
        "atr_14": 2,
        "return_20": 0.05 if side == "BULL" else -0.05,
        "sma_50_distance": 0.02 if side == "BULL" else -0.02,
        "adv_20": 10_000_000,
        "as_of": NOW.isoformat(),
    }
    lines, sides = build_lines("TEST", feature, NOW)
    line = next(r for r in lines if r["kind"] == "Swing")
    selected = next(
        r for r in sides if r["line_id"] == line["id"] and r["side"] == side
    )
    quotes = [quote()] if side == "BULL" else [quote("P", delta=-0.5)]
    selected["payload"]["trade"] = long_options("TEST", 100, quotes, NOW)[side]
    return (
        paper_pick(line, selected, feature, ["fixture-bar"], NOW),
        feature,
        line,
        selected,
    )


def test_concrete_contract_uses_ask_not_mid_and_no_quantity():
    trade = long_options("TEST", 100, [quote()], NOW)["BULL"]
    assert trade["max_loss"] == pytest.approx(220)
    assert trade["contract"]["breakeven"] == pytest.approx(102.2)
    assert trade["contract"]["executable"] is False
    assert "quantity" not in trade


@pytest.mark.parametrize(
    "item",
    [
        quote(bid=3, ask=2),
        quote(bid=0),
        quote(delta=0.1),
        quote(ask=4),
        quote(delta=float("nan")),
    ],
)
def test_unusable_quotes_are_not_selected(item):
    assert not long_options("TEST", 100, [item], NOW)


def test_future_and_stale_quotes_rejected():
    for stamp in (NOW + timedelta(seconds=1), NOW - timedelta(days=5)):
        item = quote()
        item["latestQuote"]["t"] = stamp.isoformat()
        assert not long_options("TEST", 100, [item], NOW)


def test_paper_publication_has_no_validated_probability():
    pick, _, _, _ = make_pick()
    assert pick["payload"]["status"] == "UNVALIDATED_PAPER_RESEARCH"
    assert pick["payload"]["probability"] is None
    assert pick["observations"] == ["fixture-bar"]


def test_disagreeing_trend_and_low_liquidity_prevent_publication():
    _, feature, line, side = make_pick()
    feature["sma_50_distance"] = -0.01
    assert paper_pick(line, side, feature, [], NOW) is None
    feature["sma_50_distance"] = 0.01
    feature["adv_20"] = 1000
    assert paper_pick(line, side, feature, [], NOW) is None


@pytest.mark.parametrize(
    "side,close,result,pnl",
    [
        ("BULL", 108, "win", 580),
        ("BULL", 101, "loss", -120),
        ("BEAR", 90, "win", 780),
        ("BEAR", 105, "loss", -220),
    ],
)
def test_winners_and_losers_use_option_payoff_not_direction(side, close, result, pnl):
    pick, _, _, _ = make_pick(side)
    original = deepcopy(pick)
    expiry = datetime.fromisoformat(pick["expires_at"])
    bar = {
        "id": "fixture-close",
        "session_date": "2026-11-06",
        "close": close,
        "as_of": expiry.isoformat(),
        "available_at": expiry.isoformat(),
        "source": "fixture",
        "feed": "fixture",
    }
    outcome = expiration_outcome(pick, bar, expiry + timedelta(minutes=1))
    assert outcome["payload"]["result"] == result
    assert outcome["payload"]["hypothetical_pnl"] == pytest.approx(pnl)
    assert outcome["payload"]["contract_pnl"] is None
    assert outcome["payload"]["fill_assumed"] is False
    assert pick == original
    if side == "BULL" and close == 101:
        assert outcome["payload"]["direction_result"] == "win"


def test_grading_requires_exact_session_and_no_future_data():
    pick, _, _, _ = make_pick()
    expiry = datetime.fromisoformat(pick["expires_at"])
    bar = {"session_date": "2026-11-05"}
    with pytest.raises(ValueError, match="Exact expiration"):
        expiration_outcome(pick, bar, expiry)
    bar = {
        "session_date": "2026-11-06",
        "close": 100,
        "as_of": (expiry + timedelta(days=1)).isoformat(),
    }
    with pytest.raises(ValueError, match="Future"):
        expiration_outcome(pick, bar, expiry)


def test_quote_refresh_cannot_renew_old_option_research():
    from engine.trade_research import research_is_fresh

    payload = {
        "research_retrieved_at": (NOW - timedelta(hours=2)).isoformat(),
        "retrieved_at": NOW.isoformat(),
    }
    assert not research_is_fresh(payload, NOW)
    assert not research_is_fresh({}, NOW)
    assert not research_is_fresh(
        {"research_retrieved_at": (NOW + timedelta(minutes=1)).isoformat()}, NOW
    )
    assert research_is_fresh(
        {"research_retrieved_at": (NOW - timedelta(minutes=5)).isoformat()}, NOW
    )
