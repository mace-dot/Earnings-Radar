"""Verify mechanical quote arithmetic used by Earnings Radar."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from earnings_radar.calculations import (
    contract_cost,
    enrich_quote_row,
    expiration_breakevens,
    mid_price,
    realized_pnl,
    spread_pct,
    straddle_purchase_cost,
)
from earnings_radar.flags import liquidity_flags, research_quality_flags


def test_spread_pct_mid_based():
    # bid 4.80, ask 5.00 → mid 4.90 → spread 0.20 / 4.90 ≈ 4.0816%
    assert spread_pct(4.80, 5.00) == pytest.approx(4.081632653061225)


def test_straddle_and_contract_cost():
    cost = straddle_purchase_cost(5.00, 4.80)
    assert cost == pytest.approx(9.80)
    assert contract_cost(cost) == pytest.approx(980.0)


def test_expiration_breakevens():
    lo, hi = expiration_breakevens(100, 5.00, 4.80)
    assert lo == pytest.approx(90.2)
    assert hi == pytest.approx(109.8)


def test_realized_pnl_debit_spread():
    # Entry 9.80, exit 12.00, 1 contract, $2 fees → (2.20 * 100) - 2 = 218
    assert realized_pnl(9.80, 12.00, contracts=1, fees=2) == pytest.approx(218.0)


def test_enrich_quote_row_sample_aaa_atm():
    row = enrich_quote_row(
        {
            "stock_price": 100.0,
            "strike": 100.0,
            "call_bid": 4.80,
            "call_ask": 5.00,
            "put_bid": 4.60,
            "put_ask": 4.80,
        }
    )
    assert row["straddle_ask_cost"] == pytest.approx(9.80)
    assert row["contract_cost"] == pytest.approx(980.0)
    assert row["breakeven_low"] == pytest.approx(90.2)
    assert row["breakeven_high"] == pytest.approx(109.8)
    assert row["straddle_cost_pct_of_spot"] == pytest.approx(9.8)


def test_research_and_liquidity_flags_separate():
    research = research_quality_flags(
        {
            "confirmation_status": "Unconfirmed",
            "source": "",
        },
        note_count=0,
    )
    assert "unconfirmed_earnings" in research
    assert "missing_earnings_source" in research
    assert "no_research_notes" in research

    liq = liquidity_flags(
        {
            "stock_price": 50,
            "strike": 50,
            "expiration": "2026-10-16",
            "call_bid": 1.10,
            "call_ask": 1.80,
            "put_bid": 1.00,
            "put_ask": 1.70,
            "quote_timestamp": "2026-10-01T18:00:00+00:00",
            "call_volume": 5,
            "put_volume": 3,
            "call_open_interest": 20,
            "put_open_interest": 15,
        },
        earnings_date="2026-10-22",
        now=datetime(2026, 10, 6, 17, 0, tzinfo=timezone.utc),
        stale_hours=24,
        wide_spread_pct=15,
    )
    assert any(f.startswith("stale_quote:") for f in liq)
    assert any(f.startswith("wide_call_spread:") for f in liq)
    assert any(f.startswith("wide_put_spread:") for f in liq)
    assert "low_volume" in liq
    assert "low_open_interest" in liq
    assert "expiration_before_earnings" in liq
    assert "unconfirmed_earnings" not in liq


def test_expiration_before_earnings_only_when_earlier():
    flags = liquidity_flags(
        {
            "stock_price": 80,
            "strike": 80,
            "expiration": "2026-10-20",
            "call_bid": 3.0,
            "call_ask": 3.2,
            "put_bid": 2.9,
            "put_ask": 3.1,
            "quote_timestamp": "2026-10-06T16:00:00+00:00",
            "call_volume": 200,
            "put_volume": 180,
            "call_open_interest": 3000,
            "put_open_interest": 2800,
        },
        earnings_date="2026-10-28",
        now=datetime(2026, 10, 6, 17, 0, tzinfo=timezone.utc),
    )
    assert "expiration_before_earnings" in flags


def test_missing_fields_flag():
    flags = liquidity_flags(
        {
            "stock_price": None,
            "strike": 195,
            "expiration": "2026-11-13",
            "call_bid": None,
            "call_ask": None,
            "put_bid": None,
            "put_ask": None,
            "quote_timestamp": "2026-10-06T15:45:00+00:00",
        },
        earnings_date="2026-11-05",
        now=datetime(2026, 10, 6, 17, 0, tzinfo=timezone.utc),
    )
    assert any(f.startswith("missing_fields:") for f in flags)


def test_mid_price_none_on_incomplete():
    assert mid_price(None, 5.0) is None
    assert spread_pct(5.0, 4.0) is None  # ask < bid
