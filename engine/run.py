"""Bounded scheduled jobs. Provider failures remain observable, never empty successes."""

import argparse
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

from engine.calendar import reconcile
from engine.features import price_features
from engine.move_features import setup_features
from engine.sectors import enrich
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
    previous = {
        r["symbol"]: r
        for r in store.pages("securities", {"select": "*", "order": "symbol.asc"})
    }
    for row in rows:
        prior = previous.get(row["symbol"], {})
        if prior.get("sector") not in {
            None,
            "Unclassified",
            "Classification unavailable",
        }:
            for key in ("sector", "industry", "sector_etf"):
                if key in prior:
                    row[key] = prior[key]
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
                    (now - timedelta(days=30)).date().isoformat(),
                    (now + timedelta(days=60)).date().isoformat(),
                )
            )
        except Exception as exc:
            errors.append(
                {"provider": provider.__name__, "error_type": type(exc).__name__}
            )
    if not observations:
        raise RuntimeError("No calendar feed available; cached events preserved")
    events = reconcile(observations, datetime.now(timezone.utc))
    securities = store.pages("securities", {"select": "symbol", "order": "symbol.asc"})
    known = {row["symbol"] for row in securities}
    events = [row for row in events if row["symbol"] in known]
    for offset in range(0, len(events), 300):
        store.write("earnings_events", events[offset : offset + 300])
    return {"events": len(events), "provider_errors": errors}


def prices(store: Store, now: datetime, symbols: list[str]) -> dict[str, Any]:
    observations = []
    provider = Alpaca()
    for offset in range(0, len(symbols), 100):
        observations.extend(
            provider.bars(
                symbols[offset : offset + 100],
                (now - timedelta(days=420)).date().isoformat(),
                now.date().isoformat(),
            )
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
    missing_prices = 0
    for offset in range(0, len(symbols), 100):
        batch = symbols[offset : offset + 100]
        membership = "in.(" + ",".join(batch) + ")"
        all_bars = store.pages(
            "daily_bars",
            {"symbol": membership, "order": "symbol.asc,session_date.asc"},
            capacity=60000,
        )
        all_events = store.pages(
            "earnings_events",
            {
                "symbol": membership,
                "report_date": f"gte.{now.date()}",
                "order": "report_date.asc,id.asc",
            },
        )
        contexts = store.pages(
            "market_observations",
            {"symbol": membership, "order": "retrieved_at.desc,id.asc"},
        )
        feature_rows, line_rows, side_rows, pick_rows = [], [], [], []
        for symbol in batch:
            bars = [row for row in all_bars if row["symbol"] == symbol][-500:]
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
            feature = {
                **price_features(observations, now),
                **setup_features(observations, now),
            }
            if not bars:
                missing_prices += 1
            feature_rows.append(
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
            )
            event = next((row for row in all_events if row["symbol"] == symbol), None)
            context = next((row for row in contexts if row["symbol"] == symbol), None)
            estimate = context["payload"].get("option_estimate") if context else None
            if estimate and (
                not event or estimate.get("report_date") != event["report_date"]
            ):
                estimate = None
            lines, sides = build_lines(symbol, feature, now, event, estimate)
            from engine.trade_research import paper_pick

            research_trades = (
                (context or {}).get("payload", {}).get("research_trades", {})
            )
            for side in sides:
                line = next(item for item in lines if item["id"] == side["line_id"])
                trade = research_trades.get(side["side"])
                # A fresh collection must confirm the chain; old cached research cannot create new picks.
                if (
                    line["kind"] == "Swing"
                    and trade
                    and context
                    and now - datetime.fromisoformat(context["retrieved_at"])
                    < timedelta(hours=1)
                ):
                    side["payload"]["trade"] = trade
                    pick = paper_pick(
                        line,
                        side,
                        feature,
                        [row["id"] for row in bars] + [context["id"]],
                        now,
                    )
                    if pick:
                        pick_rows.append(pick)
            for line in lines:
                line["payload"]["metrics"] = {
                    key: feature.get(key)
                    for key in (
                        "return_20",
                        "rv_10",
                        "rv_60",
                        "vol_compression_ratio",
                        "bb_width_percentile",
                        "move_meter",
                    )
                }
                line["payload"]["option_estimate"] = estimate
                line["payload"]["source"] = "Alpaca IEX daily bars"
            line_rows.extend(lines)
            side_rows.extend(sides)
            count += len(lines)
        store.write("features", feature_rows)
        store.write("lines", line_rows)
        for index in range(0, len(side_rows), 400):
            store.write("line_sides", side_rows[index : index + 400])
        store.write("picks", pick_rows, immutable=True)
    return {
        "lines": count,
        "symbols": len(symbols),
        "symbols_without_price_history": missing_prices,
        "model_status": "unvalidated",
        "automatic_trade_execution": False,
    }


def calendar_symbols(store: Store, now: datetime) -> list[str]:
    events = store.pages(
        "earnings_events",
        {
            "select": "symbol",
            "order": "id.asc",
            "and": f"(report_date.gte.{(now-timedelta(days=20)).date()},report_date.lte.{(now+timedelta(days=60)).date()})",
        },
    )
    queued = store.pages("score_queue", {"select": "symbol", "order": "symbol.asc"})
    existing = store.pages("lines", {"select": "symbol", "order": "id.asc"})
    return sorted({row["symbol"] for row in events + queued + existing})


def drain_queue(store: Store, limit: int = 10) -> dict[str, int]:
    rows = store.rpc("radar_claim_scores", {"p_limit": limit})
    completed = 0
    for row in rows:
        symbol = row["symbol"]
        try:
            securities = store.read(
                "securities", {"symbol": f"eq.{symbol}", "limit": "1"}
            )
            store.write("securities", [enrich(securities[0])], "symbol")
            prices(store, datetime.now(timezone.utc), [symbol])
            from engine.research import market_context, news_context

            events = store.read(
                "earnings_events",
                {
                    "symbol": f"eq.{symbol}",
                    "report_date": f"gte.{datetime.now(timezone.utc).date()}",
                    "order": "report_date.asc",
                    "limit": "1",
                },
            )
            market_context(store, symbol, events[0]["report_date"] if events else None)
            news_context(store, symbol)
            score(store, datetime.now(timezone.utc), [symbol])
            store.finish_score(symbol)
            completed += 1
        except Exception as exc:
            store.finish_score(symbol, type(exc).__name__)
    return {"claimed": len(rows), "completed": completed}


def sectors(store: Store, symbols: list[str], limit: int = 100) -> dict[str, int]:
    changed = 0
    wanted = set(symbols)
    candidates = store.pages(
        "securities", {"select": "*", "order": "as_of.asc,symbol.asc"}
    )
    selected = [
        r
        for r in candidates
        if r["symbol"] in wanted
        and r["sector"] in {"Unclassified", "Classification unavailable"}
    ]
    for row in selected[:limit]:
        try:
            store.write("securities", [enrich(row)], "symbol")
            changed += 1
        except Exception:
            continue

    return {"sector_enriched": changed}


def grade(store: Store, now: datetime) -> dict[str, int]:
    from engine.trade_research import expiration_outcome, VERSION

    picks = store.pages(
        "picks",
        {
            "expires_at": f"lte.{now.isoformat()}",
            "strategy_version": f"eq.{VERSION}",
            "order": "id.asc",
        },
    )
    outcomes = {
        row["pick_id"]
        for row in store.pages(
            "pick_outcomes", {"select": "pick_id", "order": "id.asc"}
        )
    }
    pending = [p for p in picks if p["id"] not in outcomes]
    if pending:
        prices(store, now, sorted({p["symbol"] for p in pending})[:100])
    graded = 0
    for pick in pending[:100]:
        expiry = pick["payload"]["trade"]["contract"]["expiry"]
        bars = store.read(
            "daily_bars",
            {
                "symbol": f"eq.{pick['symbol']}",
                "session_date": f"eq.{expiry}",
                "feed": "eq.iex_split_adjusted",
                "order": "available_at.desc",
                "limit": "1",
            },
        )
        if not bars:
            continue
        store.write(
            "pick_outcomes", [expiration_outcome(pick, bars[0], now)], immutable=True
        )
        graded += 1
    return {"graded": graded, "awaiting_expiration_close": len(pending) - graded}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "job",
        choices=[
            "universe",
            "calendar",
            "prices",
            "score",
            "queue",
            "context",
            "doctor",
            "sectors",
            "history_backfill",
            "grade",
            "market_scan",
        ],
    )
    parser.add_argument("--symbols", default="")
    parser.add_argument("--batches", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.batches <= 100:
        parser.error("--batches must be between 1 and 100")
    now = datetime.now(timezone.utc)
    if args.job == "doctor":
        from engine.doctor import main as doctor

        doctor()
        return
    store = Store()
    job = args.job
    symbols = [
        value.strip().upper() for value in args.symbols.split(",") if value.strip()
    ]
    if not symbols and job in {"prices", "score", "context", "sectors"}:
        symbols = calendar_symbols(store, now)
    try:
        if job == "market_scan":
            from engine.market_scan import market_scan

            totals = {"claimed": 0, "covered": 0, "unavailable": 0}
            for _ in range(args.batches):
                result = market_scan(store)
                for key in totals:
                    totals[key] += result.get(key, 0)
                if not result["claimed"]:
                    break
            payload = totals
        elif job == "grade":
            payload = grade(store, now)
        elif job == "history_backfill":
            from engine.providers.history import alpha_earnings

            symbols = symbols or calendar_symbols(store, now)[:1]
            rows = []
            for symbol in symbols[:1]:
                rows.extend(alpha_earnings(symbol))
            store.write("earnings_events", rows)
            payload = {"historical_reports": len(rows)}
        elif job == "sectors":
            payload = sectors(store, symbols)
        elif job == "queue":
            payload = drain_queue(store)
        elif job == "context":
            from engine.research import market_context, news_context

            if not args.symbols:
                candidates = store.pages("features", {"order": "as_of.desc,id.asc"})
                eligible = {
                    row["symbol"]
                    for row in candidates
                    if (row["values"].get("last_close") or 0) >= 5
                    and (row["values"].get("adv_20") or 0) >= 5000000
                }
                contexts = store.pages(
                    "market_observations",
                    {
                        "select": "symbol,retrieved_at",
                        "order": "retrieved_at.desc,id.asc",
                    },
                )
                latest = {}
                for row in contexts:
                    latest.setdefault(row["symbol"], row["retrieved_at"])
                symbols = sorted(
                    (symbol for symbol in symbols if symbol in eligible),
                    key=lambda s: (latest.get(s, ""), s),
                )[:10]
            results = {}
            errors = []
            for symbol in symbols:
                try:
                    events = store.read(
                        "earnings_events",
                        {
                            "symbol": f"eq.{symbol}",
                            "report_date": f"gte.{now.date()}",
                            "order": "report_date.asc",
                            "limit": "1",
                        },
                    )
                    results[symbol] = {
                        "market": market_context(
                            store, symbol, events[0]["report_date"] if events else None
                        ),
                        "news": news_context(store, symbol),
                    }
                except Exception as exc:
                    import httpx

                    errors.append(
                        {
                            "symbol": symbol,
                            "error_type": type(exc).__name__,
                            "http_status": (
                                exc.response.status_code
                                if isinstance(exc, httpx.HTTPStatusError)
                                else None
                            ),
                        }
                    )
            payload = {
                "processed_symbols": len(results),
                "provider_errors": errors,
                "provider_failures": sum(
                    len(value["news"].get("errors", [])) for value in results.values()
                ),
            }
            score(store, datetime.now(timezone.utc), symbols)
        else:
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
