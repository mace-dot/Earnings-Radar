import httpx
import pytest

from engine.run import safe_diagnostic
from engine.store import DatabaseOperationError, Store


def database(handler):
    db = Store.__new__(Store)
    db.url = "https://fixture.supabase.co"
    db.client = httpx.Client(transport=httpx.MockTransport(handler))
    return db


def test_history_timeout_retries_then_succeeds_without_logging_body(
    monkeypatch, caplog
):
    calls = []
    sleeps = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            500 if len(calls) == 1 else 200,
            json=(
                {"code": "57014", "message": "private-body"}
                if len(calls) == 1
                else 12592
            ),
        )

    monkeypatch.setattr("engine.store.time.sleep", sleeps.append)
    assert (
        database(handler).rpc("radar_index_history", {"p_sessions": ["2026-10-08"]})
        == 12592
    )
    assert len(calls) == 2
    assert sleeps == [1]
    assert "57014" in caplog.text and "attempts=1" in caplog.text
    assert "private-body" not in caplog.text


@pytest.mark.parametrize(
    "status,code", [(401, "57014"), (403, "42501"), (500, "private-secret")]
)
def test_auth_and_unknown_errors_are_not_retried(status, code):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"code": code, "message": "private-body"})

    with pytest.raises(DatabaseOperationError) as caught:
        database(handler).rpc("radar_index_history", {})
    assert len(calls) == 1
    diagnostic = safe_diagnostic(caught.value)
    assert "radar_index_history" in diagnostic
    assert "private" not in diagnostic


def test_timeout_retries_are_bounded_and_failure_stays_failed(monkeypatch):
    calls = []
    monkeypatch.setattr("engine.store.time.sleep", lambda _: None)

    def handler(request):
        calls.append(request)
        return httpx.Response(500, json={"code": "57014"})

    with pytest.raises(DatabaseOperationError, match="attempts=3"):
        database(handler).rpc("radar_index_history", {})
    assert len(calls) == 3


def test_queue_claims_are_never_replayed():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(500, json={"code": "40001"})

    with pytest.raises(DatabaseOperationError):
        database(handler).rpc("radar_claim_market", {})
    assert len(calls) == 1
