from datetime import datetime, timedelta, timezone

import httpx
import pytest

from engine.providers.public_market import Cboe, Nasdaq, number


def test_public_history_keeps_source_adjustment_limit_and_no_forming_bar():
    now = datetime.now(timezone.utc)
    past = (now - timedelta(days=2)).strftime("%m/%d/%Y")
    future = (now + timedelta(days=2)).strftime("%m/%d/%Y")
    provider = Nasdaq()
    provider.client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "data": {
                        "totalRecords": 2,
                        "tradesTable": {
                            "rows": [
                                {
                                    "date": date,
                                    "close": "$100.00",
                                    "open": "99",
                                    "high": "102",
                                    "low": "98",
                                    "volume": "1,000",
                                }
                                for date in [past, future]
                            ]
                        },
                    }
                },
            )
        )
    )
    rows = provider.bars(["FIXTURE"], "2020-01-01", "2030-01-01")
    assert len(rows) == 1
    assert rows[0].source == "Nasdaq"
    assert rows[0].values["adjustment_status"] == "unspecified"
    assert rows[0].available_at >= rows[0].observed_at


def test_public_quote_failure_is_not_bypassed():
    provider = Nasdaq()
    provider.client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(429))
    )
    with pytest.raises(httpx.HTTPStatusError):
        provider.bars(["FIXTURE"], "2020-01-01", "2030-01-01")


def test_cboe_delayed_snapshot_keeps_time_semantics():
    stamp = (datetime.now(timezone.utc) - timedelta(minutes=20)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    provider = Cboe()
    provider.client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "timestamp": stamp,
                    "data": {
                        "options": [
                            {
                                "option": "FIXTURE261106C00100000",
                                "bid": 2,
                                "ask": 2.2,
                                "delta": 0.5,
                            }
                        ]
                    },
                },
            )
        )
    )
    row = provider.snapshots("FIXTURE")[0]
    assert row.feed == "cboe_delayed"
    assert "individual quote age unknown" in row.values["quote_timestamp_kind"]
    assert row.values["greeks"]["delta"] == 0.5
    assert row.observed_at < row.available_at


def test_malformed_numbers_are_not_prices():
    assert number("$1,234.56") == 1234.56
    assert number("--") is None
    assert number("NaN") is None


def test_one_symbol_timeout_does_not_discard_other_symbols():
    provider = Nasdaq()

    def response(request):
        if "/TIMEOUT/" in request.url.path:
            raise httpx.ReadTimeout("fixture timeout", request=request)
        return httpx.Response(200, json={"data": {"tradesTable": {"rows": []}}})

    provider.client = httpx.Client(transport=httpx.MockTransport(response))
    assert provider.bars(["TIMEOUT", "EMPTY"], "2020-01-01", "2030-01-01") == []
    assert provider.errors == {"TIMEOUT": "ReadTimeout"}


def test_transport_outage_does_not_submit_the_entire_symbol_queue():
    provider = Nasdaq()
    requested = []

    def response(request):
        requested.append(request.url.path)
        raise httpx.ReadTimeout("fixture timeout", request=request)

    provider.client = httpx.Client(transport=httpx.MockTransport(response))
    assert (
        provider.bars(["ONE", "TWO", "THREE", "FOUR"], "2020-01-01", "2030-01-01") == []
    )
    assert len(requested) == 2
    assert "halted" in provider.errors["THREE"]
