"""Read-only connectivity checks. Never print keys, URLs containing tokens or bodies."""

from datetime import datetime, timedelta, timezone
from typing import Callable

import httpx

from engine.providers.alpha_vantage import AlphaVantage
from engine.providers.market import Finnhub
from engine.providers.public_market import Cboe
from engine.providers.daily_history import history_provider
from engine.providers.sec import SEC
from engine.store import ConfigurationError, Store


def check(name: str, operation: Callable[[], object]) -> dict[str, str]:
    try:
        operation()
        return {"provider": name, "status": "OK"}
    except ConfigurationError as exc:
        return {"provider": name, "status": "FAIL", "reason": str(exc)}
    except httpx.HTTPStatusError as exc:
        return {
            "provider": name,
            "status": "FAIL",
            "reason": f"HTTP {exc.response.status_code}",
        }
    except Exception as exc:
        return {"provider": name, "status": "FAIL", "reason": type(exc).__name__}


def require_observations(operation: Callable[[], object]) -> object:
    result = operation()
    if not result:
        raise RuntimeError("Provider returned no usable observations")
    return result


def main() -> None:
    now = datetime.now(timezone.utc)
    start, end = now.date().isoformat(), (now + timedelta(days=7)).date().isoformat()
    checks = [
        (
            "Supabase",
            lambda: Store().read("securities", {"select": "symbol", "limit": "1"}),
        ),
        ("SEC", lambda: SEC().fundamentals("0000320193")),
        (
            "Daily price history",
            lambda: require_observations(
                lambda: history_provider(Store()).bars(
                    ["MU"], (now - timedelta(days=10)).date().isoformat(), start
                )
            ),
        ),
        ("Cboe delayed options", lambda: Cboe().snapshots("MU")),
        ("Finnhub quote", lambda: Finnhub().quote("MU")),
        ("Finnhub", lambda: Finnhub().calendar(start, end)),
        ("Alpha Vantage", lambda: AlphaVantage().calendar(start, end)),
    ]
    failures = []
    for name, operation in checks:
        result = check(name, operation)
        print(f"{name}: {result['status']} {result.get('reason', '')}")
        if result["status"] == "FAIL" and name != "Alpha Vantage":
            failures.append(name)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
