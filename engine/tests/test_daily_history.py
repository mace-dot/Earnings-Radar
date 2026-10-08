from datetime import datetime, timezone

import httpx
import pytest

from engine.providers.daily_history import (
    Massive,
    collect_day,
    session_close,
    history_provider,
)

NOW = datetime(2026, 10, 8, 16, tzinfo=timezone.utc)


def test_exchange_close_accounts_for_half_days():
    assert session_close("2026-11-27").hour == 18
    assert session_close("2026-10-07").hour == 20


def test_archive_reuses_original_availability_and_source():
    class Database:
        def rpc(self, name, payload):
            assert name == "radar_history_bars"
            return [
                {
                    "symbol": "FIXTURE",
                    "session_date": "2026-10-07",
                    "source": "Massive",
                    "feed": "massive_daily_adjusted",
                    "observed_at": "2026-10-07T20:00:00+00:00",
                    "available_at": NOW.isoformat(),
                    "open": 99,
                    "high": 102,
                    "low": 98,
                    "close": 100,
                    "volume": 1000,
                }
            ]

    row = Massive(Database()).bars(["FIXTURE"], "2026-01-01", "2026-10-08")[0]
    assert row.available_at == NOW
    assert row.source == "Massive"
    with pytest.raises(ValueError):
        row.at(datetime(2026, 10, 7, tzinfo=timezone.utc))


def test_denied_history_entitlement_is_not_empty_success(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "fixture-only")

    def denied(*args, **kwargs):
        return httpx.Response(
            403, request=httpx.Request("GET", "https://api.massive.com/fixture")
        )

    monkeypatch.setattr("engine.providers.daily_history.httpx.get", denied)
    with pytest.raises(httpx.HTTPStatusError):
        collect_day(None, "2026-10-07", NOW)


def test_unverified_adjustment_is_not_accepted(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "fixture-only")
    monkeypatch.setattr(
        "engine.providers.daily_history.httpx.get",
        lambda *a, **kw: httpx.Response(
            200,
            json={"adjusted": False, "results": [{"T": "FIXTURE", "c": 100}]},
            request=httpx.Request("GET", "https://api.massive.com/fixture"),
        ),
    )
    with pytest.raises(RuntimeError):
        collect_day(None, "2026-10-07", NOW)


def test_missing_key_keeps_existing_source(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    fixture = object()
    assert history_provider(None, lambda: fixture) is fixture


def test_grouped_archive_keeps_original_source_and_exact_volume(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "fixture-only")
    request = httpx.Request("GET", "https://api.massive.com/fixture")
    monkeypatch.setattr(
        "engine.providers.daily_history.httpx.get",
        lambda *a, **kw: httpx.Response(
            200,
            request=request,
            json={
                "adjusted": True,
                "results": [
                    {
                        "T": "FIXTURE",
                        "o": 99,
                        "h": 101,
                        "l": 98,
                        "c": 100,
                        "v": 149588.0,
                    },
                    {"T": "FRACTIONAL", "o": 99, "h": 101, "l": 98, "c": 100, "v": 1.5},
                ],
            },
        ),
    )

    class Database:
        saved = []

        def write(self, table, rows, immutable=False):
            assert table == "market_history_days" and immutable
            self.saved.extend(rows)

    db = Database()
    assert collect_day(db, "2026-10-07", NOW) == 2
    assert db.saved[0]["source"] == "Massive"
    assert db.saved[0]["payload"]["results"][0]["v"] == 149588
    assert isinstance(db.saved[0]["payload"]["results"][0]["v"], int)
    assert db.saved[0]["payload"]["results"][1]["v"] is None


def test_history_rpc_paginates_past_supabase_default_row_cap():
    from engine.store import Store

    db = Store.__new__(Store)
    db.url = "https://fixture.supabase.co"
    dataset = [
        {"symbol": f"FIXTURE{i:05}", "session_date": "2026-10-07"} for i in range(2037)
    ]

    def response(request):
        offset = int(request.url.params["offset"])
        return httpx.Response(200, json=dataset[offset : offset + 1000])

    db.client = httpx.Client(transport=httpx.MockTransport(response))
    result = db.rpc(
        "radar_history_bars",
        {"p_symbols": ["FIXTURE"], "p_start": "2026-01-01", "p_end": "2026-10-08"},
    )
    assert result == dataset


def test_provider_diagnostic_reports_status_without_exposing_credentials_or_body():
    from engine.run import safe_diagnostic

    request = httpx.Request(
        "GET", "https://api.massive.com/fixture?apiKey=fixture-secret"
    )
    response = httpx.Response(
        403, request=request, text="fixture-private-provider-body"
    )
    error = httpx.HTTPStatusError(
        "fixture-private-error", request=request, response=response
    )
    message = safe_diagnostic(error)
    assert "HTTP 403" in message
    assert "fixture-secret" not in message
    assert "fixture-private" not in message
