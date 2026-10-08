import pytest

from engine.doctor import check
from engine import doctor
from engine.store import ConfigurationError, database_configuration


@pytest.fixture(autouse=True)
def clean_database_environment(monkeypatch):
    for name in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_missing_url_is_distinguished_from_missing_key(monkeypatch):
    with pytest.raises(ConfigurationError, match="SUPABASE_URL is missing"):
        database_configuration()
    monkeypatch.setenv("SUPABASE_URL", "https://fixture.supabase.co")
    with pytest.raises(ConfigurationError, match="SERVICE_ROLE_KEY.*missing"):
        database_configuration()


def test_dashboard_url_is_rejected_without_echoing_it(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.com/dashboard/project/fixture")
    result = check("Supabase", database_configuration)
    assert result["status"] == "FAIL"
    assert "project API URL" in result["reason"]
    assert "https://" not in result["reason"]


def test_new_secret_key_and_whitespace_are_supported(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", " https://fixture.supabase.co/ ")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", " sb_secret_test_fixture ")
    assert database_configuration() == (
        "https://fixture.supabase.co",
        "sb_secret_test_fixture",
    )


@pytest.mark.parametrize("key", ["sbp_test_fixture", "sb_publishable_test_fixture"])
def test_wrong_key_type_is_rejected_without_disclosure(monkeypatch, key):
    monkeypatch.setenv("SUPABASE_URL", "https://fixture.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", key)
    result = check("Supabase", database_configuration)
    assert result["status"] == "FAIL"
    assert key not in result["reason"]


def test_doctor_fails_when_required_connection_fails(monkeypatch):
    monkeypatch.setattr(
        doctor,
        "check",
        lambda name, operation: {
            "provider": name,
            "status": "FAIL" if name == "Supabase" else "OK",
        },
    )
    with pytest.raises(SystemExit) as failure:
        doctor.main()
    assert failure.value.code == 1


def test_optional_history_credential_does_not_fail_doctor(monkeypatch):
    monkeypatch.setattr(
        doctor,
        "check",
        lambda name, operation: {
            "provider": name,
            "status": "FAIL" if name == "Alpha Vantage" else "OK",
        },
    )
    doctor.main()
