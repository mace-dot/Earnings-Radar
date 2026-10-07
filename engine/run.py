"""Bounded scheduled jobs. Provider failures remain observable, never empty successes."""

import argparse
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from engine.calendar import reconcile
from engine.features import price_features
from engine.lines import build_lines
from engine.providers.base import Observation
from engine.providers.market import Alpaca, Finnhub
from engine.providers.alpha_vantage import AlphaVantage
from engine.providers.sec import SEC
from engine.store import Store


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def universe(store: Store) -> dict[str, Any]:
    rows = SEC().securities()
    for offset in range(0, len(rows), 400):
        store.write("securities", rows[offset : offset + 400], "symbol")
    return {
        "identifiers": len(rows),
        "asset_classification": "Not yet verified as common shares",
    }


def calendar(store: Store, now: datetime) -> dict[str, Any]:
    observations, errors = [], []
    for provider in (Finnhub, AlphaVantage):
        try:
            observations.extend(
                provider().calendar(
                    now.date().isoformat(),
                    (now + timedelta(days=60)).date().isoformat(),
                )
            )
        except Exception as exc:
            errors.append(
                {"provider": provider.__name__, "error_type": type(exc).__name__}
            )
    if not observations:
        raise RuntimeError("No calendar feed available; cached events preserved")
    events = reconcile(observations, now)
    securities = store.read("securities", {"select": "symbol", "limit": "20000"})
    known = {row["symbol"] for row in securities}
    events = [row for row in events if row["symbol"] in known]
    for offset in range(0, len(events), 300):
        store.write("earnings_events", events[offset : offset + 300])
    return {"events": len(events), "provider_errors": errors}


def prices(store: Store, now: datetime, symbols: list[str]) -> dict[str, Any]:
    observations = Alpaca().bars(
        symbols, (now - timedelta(days=420)).date().isoformat(), now.date().isoformat()
    )
    rows = []
    for observation in observations:
        bar = observation.values
        rows.append(
            {
                "id": digest(f"{observation.symbol}:{bar['t']}:{observation.feed}"),
                "symbol": observation.symbol,
                "session_date": bar["t"][:10],
                "open": bar.get("o"),
                "high": bar.get("h"),
                "low": bar.get("l"),
                "close": bar["c"],
                "volume": bar.get("v"),
                "source": observation.source,
                "feed": observation.feed,
                "as_of": observation.observed_at.isoformat(),
                "available_at": observation.available_at.isoformat(),
            }
        )
    for offset in range(0, len(rows), 400):
        store.write("daily_bars", rows[offset : offset + 400])
    return {"bars": len(rows), "symbols": symbols, "feed": "iex_split_adjusted"}


def score(store: Store, now: datetime, symbols: list[str]) -> dict[str, Any]:
    count = 0
    for symbol in symbols:
        bars = store.read(
            "daily_bars",
            {"symbol": f"eq.{symbol}", "order": "session_date.asc", "limit": "500"},
        )
        observations = [
            Observation(
                symbol,
                datetime.fromisoformat(row["as_of"]),
                datetime.fromisoformat(row["available_at"]),
                row["source"],
                {
                    "c": row["close"],
                    "h": row["high"],
                    "l": row["low"],
                    "v": row["volume"],
                },
                row["feed"],
            )
            for row in bars
        ]
        feature = price_features(observations, now)
        store.write(
            "features",
            [
                {
                    "id": f"{symbol}:price-v1:{now.date()}",
                    "symbol": symbol,
                    "event_id": None,
                    "version": "price-v1",
                    "as_of": now.isoformat(),
                    "observations": [row["id"] for row in bars],
                    "values": feature,
                    "missing_reasons": [
                        key for key, value in feature.items() if value is None
                    ],
                }
            ],
        )
        events = store.read(
            "earnings_events",
            {
                "symbol": f"eq.{symbol}",
                "report_date": f"gte.{now.date()}",
                "order": "report_date.asc",
                "limit": "1",
            },
        )
        lines, sides = build_lines(symbol, feature, now, events[0] if events else None)
        store.write("lines", lines)
        store.write("line_sides", sides)
        count += len(lines)
    return {
        "lines": count,
        "model_status": "unvalidated",
        "automatic_trade_execution": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("job", choices=["universe", "calendar", "prices", "score"])
    parser.add_argument(
        "--symbols", default="AAPL,MSFT,NVDA,AMZN,META,GOOGL,TSLA,JPM,XOM,SPY"
    )
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    store = Store()
    job = args.job
    symbols = [
        value.strip().upper() for value in args.symbols.split(",") if value.strip()
    ]
    try:
        payload = (
            universe(store)
            if job == "universe"
            else (
                calendar(store, now)
                if job == "calendar"
                else (
                    prices(store, now, symbols)
                    if job == "prices"
                    else score(store, now, symbols)
                )
            )
        )
        status = "partial" if payload.get("provider_errors") else "completed"
    except Exception as exc:
        store.write(
            "engine_runs",
            [
                {
                    "id": f"{job}:{now.isoformat()}",
                    "job": job,
                    "as_of": now.isoformat(),
                    "status": "failed",
                    "payload": {"error_type": type(exc).__name__},
                }
            ],
        )
        print(f"{job}: failed ({type(exc).__name__}); cached data preserved")
        raise SystemExit(1) from None
    store.write(
        "engine_runs",
        [
            {
                "id": f"{job}:{now.isoformat()}",
                "job": job,
                "as_of": now.isoformat(),
                "status": status,
                "payload": payload,
            }
        ],
    )
    print(f"{job}: {status}; {payload}")


if __name__ == "__main__":
    main()
