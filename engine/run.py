"""Bounded scheduled jobs. Provider failures remain observable, never empty successes."""

import argparse
import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from engine.alpha_budget import calendar_collected, requests_used, budget_day
from engine.calendar import reconcile
from engine.features import price_features
from engine.move_features import setup_features
from engine.sectors import enrich
from engine.lines import build_lines
from engine.providers.base import Observation
from engine.providers.market import Finnhub
from engine.providers.public_market import Nasdaq
from engine.providers.daily_history import history_provider
from engine.providers.alpha_vantage import AlphaVantage, QuotaExceeded
from engine.providers.sec import SEC
from engine.store import Store


def safe_diagnostic(exc: Exception) -> str:
    """Only allow known diagnostic forms; never expose arbitrary provider bodies."""
    if str(exc) in {
        "MASSIVE_API_KEY missing; add a historical-data key securely",
        "MASSIVE_API_KEY missing; a historical-data account is required",
    }:
        return str(exc)
    if (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.request.url.host == "api.massive.com"
    ):
        return f"Massive API HTTP {exc.response.status_code}; verify key, account entitlement and rate limit"
    match = re.fullmatch(r"(Database|Queue) operation failed \((\d{3})\)", str(exc))
    if match:
        return f"{match[1]} HTTP {match[2]}"
    if re.fullmatch(
        r"Market scan provider failed \((HTTP \d{3}|[A-Za-z]+)\); attempts recorded",
        str(exc),
    ):
        return str(exc)
    return "See per-source observation status"


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
        if prior.get("listing_metadata"):
            row["listing_metadata"] = prior["listing_metadata"]
            row["asset_type"] = prior["asset_type"]
        if prior.get("sector") not in {
            None,
            "Unclassified",
            "Classification unavailable",
        }:
            for key in ("sector", "industry", "sector_etf"):
                if key in prior:
                    row[key] = prior[key]
    # PostgREST bulk upserts require identical keys. Keep optional enrichment
    # absent for unclassified names rather than overwriting it with null.
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(tuple(sorted(row)), []).append(row)
    for group in groups.values():
        for offset in range(0, len(group), 400):
            store.write("securities", group[offset : offset + 400], "symbol")
    return {
        "identifiers": len(rows),
        "asset_classification": "Not yet verified as common shares",
    }


def calendar(store: Store, now: datetime) -> dict[str, Any]:
    observations, errors = [], []
    av_requests: list[dict[str, str]] = []
    day_start = now.astimezone(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    runs = store.read(
        "engine_runs",
        {
            "select": "job,as_of,status,payload",
            "as_of": f"gte.{day_start.isoformat()}",
            "order": "as_of.desc",
            "limit": "500",
        },
    )
    skip_alpha = (
        calendar_collected(runs, budget_day(now))
        or requests_used(runs, budget_day(now)) >= 24
    )
    for provider in (Finnhub, AlphaVantage):
        if provider is AlphaVantage and skip_alpha:
            continue
        try:
            observations.extend(
                provider().calendar(
                    (now - timedelta(days=30)).date().isoformat(),
                    (now + timedelta(days=60)).date().isoformat(),
                )
            )
            if provider is AlphaVantage:
                av_requests.append({"function": "EARNINGS_CALENDAR", "status": "ok"})
        except QuotaExceeded:
            av_requests.append({"function": "EARNINGS_CALENDAR", "status": "quota"})
            errors.append(
                {"provider": provider.__name__, "error_type": "QuotaExceeded"}
            )
        except Exception as exc:
            errors.append(
                {"provider": provider.__name__, "error_type": type(exc).__name__}
            )
            if provider is AlphaVantage:
                av_requests.append({"function": "EARNINGS_CALENDAR", "status": "error"})
    if not observations:
        raise RuntimeError("No calendar feed available; cached events preserved")
    events = reconcile(observations, datetime.now(timezone.utc))
    securities = store.pages("securities", {"select": "symbol", "order": "symbol.asc"})
    known = {row["symbol"] for row in securities}
    events = [row for row in events if row["symbol"] in known]
    for offset in range(0, len(events), 300):
        store.write("earnings_events", events[offset : offset + 300])
    return {
        "events": len(events),
        "provider_errors": errors,
        "alpha_vantage_requests": av_requests,
    }


def prices(store: Store, now: datetime, symbols: list[str]) -> dict[str, Any]:
    observations = []
    provider = history_provider(store, Nasdaq)
    for offset in range(0, len(symbols), 100):
        observations.extend(
            provider.bars(
                symbols[offset : offset + 100],
                (now - timedelta(days=420)).date().isoformat(),
                now.date().isoformat(),
            )
        )
    if symbols and not observations:
        raise RuntimeError("No usable daily history returned; cached bars preserved")
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
    return {
        "bars": len(rows),
        "symbols": symbols,
        "feed": observations[0].feed if observations else None,
        "provider_errors": provider.errors,
    }


def score(store: Store, now: datetime, symbols: list[str]) -> dict[str, Any]:
    from engine.predictive_context import bar_values, context_features, load_context

    count = 0
    missing_prices = 0
    for offset in range(0, len(symbols), 100):
        batch = symbols[offset : offset + 100]
        membership = "in.(" + ",".join(batch) + ")"
        all_bars = store.pages(
            "daily_bars",
            {"symbol": membership, "order": "symbol.asc,session_date.asc"},
            capacity=100000,
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
            {
                "symbol": membership,
                "feed": "in.(iex,finnhub_free)",
                "order": "retrieved_at.desc,id.asc",
            },
        )
        identities = store.pages(
            "securities",
            {"symbol": membership, "select": "symbol,asset_type,listing_metadata"},
        )
        financials = store.pages(
            "market_observations",
            {
                "symbol": membership,
                "feed": "eq.sec_fundamentals",
                "order": "retrieved_at.desc,id.asc",
            },
        )
        feature_rows, line_rows, side_rows, pick_rows = [], [], [], []
        context_rows = load_context(store, batch, now)
        for symbol in batch:
            matching = [row for row in all_bars if row["symbol"] == symbol]
            preferred = [row for row in matching if row["source"] == "Massive"]
            if len(preferred) < 60:
                prior = [row for row in matching if row["source"] == "Nasdaq"]
                if len(prior) > len(preferred):
                    preferred = prior
            bars = (preferred or matching)[-500:]
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
                **context_features(
                    bar_values(observations, now),
                    context_rows["events"].get(symbol, []),
                    context_rows["revisions"].get(symbol, []),
                    context_rows["implied"].get(symbol, []),
                    context_rows["spy"],
                    now,
                ),
            }
            identity = next((row for row in identities if row["symbol"] == symbol), {})
            feature["asset_type"] = identity.get("asset_type", "unverified")
            feature["listing_metadata"] = identity.get("listing_metadata", {})
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
            financial = next(
                (row for row in financials if row["symbol"] == symbol), None
            )
            financial_context = financial["payload"] if financial else None
            lines, sides = build_lines(
                symbol, feature, now, event, estimate, financial_context
            )
            from engine.trade_research import paper_pick, research_is_fresh

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
                    and research_is_fresh(context["payload"], now)
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
                line["payload"][
                    "source"
                ] = "Nasdaq / retained historical source; see each observation"
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
    existing = store.pages(
        "current_line_symbols", {"select": "symbol", "order": "symbol.asc"}
    )
    return sorted({row["symbol"] for row in events + queued + existing})


def drain_queue(store: Store, limit: int = 10) -> dict[str, Any]:
    rows = store.rpc("radar_claim_scores", {"p_limit": limit})
    completed = 0
    errors = []
    for row in rows:
        symbol = row["symbol"]
        try:
            securities = store.read(
                "securities", {"symbol": f"eq.{symbol}", "limit": "1"}
            )
            try:
                store.write("securities", [enrich(securities[0])], "symbol")
            except Exception as exc:
                errors.append(
                    {
                        "symbol": symbol,
                        "provider": "SEC classification",
                        "error_type": type(exc).__name__,
                    }
                )
            try:
                prices(store, datetime.now(timezone.utc), [symbol])
            except Exception as exc:
                from engine.history_cache import restore

                errors.append(
                    {
                        "symbol": symbol,
                        "provider": "Nasdaq history",
                        "error_type": type(exc).__name__,
                    }
                )
                restore(store, [symbol], datetime.now(timezone.utc))
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
            from engine.fundamentals import collect

            financials = collect(store, [symbol])
            errors.extend(
                {**error, "provider": "SEC fundamentals"}
                for error in financials["provider_errors"]
            )
            score(store, datetime.now(timezone.utc), [symbol])
            store.finish_score(symbol)
            completed += 1
        except Exception as exc:
            store.finish_score(symbol, type(exc).__name__)
    return {"claimed": len(rows), "completed": completed, "provider_errors": errors}


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
    from engine.trade_research import expiration_outcome, SUPPORTED_VERSIONS

    picks = store.pages(
        "picks",
        {
            "expires_at": f"lte.{now.isoformat()}",
            "strategy_version": "in.(" + ",".join(SUPPORTED_VERSIONS) + ")",
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
                "feed": "eq.nasdaq_daily_adjustment_unspecified",
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
            "listings",
            "history_backfill",
            "grade",
            "market_scan",
            "history_sync",
            "validate",
            "fundamentals",
            "alpha_scan",
            "implied_archive",
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
        if job == "listings":
            from engine.providers.listings import directory

            identities = directory()
            securities = store.pages("securities", {"order": "symbol.asc"})
            updated = [
                {**row, **identities[row["symbol"]]}
                for row in securities
                if row["symbol"] in identities
            ]
            for offset in range(0, len(updated), 300):
                store.write("securities", updated[offset : offset + 300], "symbol")
            payload = {
                "classified_identifiers": len(updated),
                "common_stock": sum(
                    row["asset_type"] == "common_stock" for row in updated
                ),
                "rule": "exchange-directory-name-v1",
            }
        elif job == "alpha_scan":
            from engine.alpha_scan import collect

            payload = collect(store, now)
        elif job == "implied_archive":
            from engine.implied_archive import collect as archive_implied

            payload = archive_implied(store, now)
        elif job == "fundamentals":
            from engine.fundamentals import collect

            symbols = symbols or calendar_symbols(store, now)
            securities = store.pages(
                "securities", {"select": "symbol,cik", "order": "symbol.asc"}
            )
            latest = store.pages(
                "market_observations",
                {
                    "feed": "eq.sec_fundamentals",
                    "select": "symbol,retrieved_at",
                    "order": "retrieved_at.desc,id.asc",
                },
            )
            seen = {}
            for row in latest:
                seen.setdefault(row["symbol"], row["retrieved_at"])
            selected = sorted(
                (r for r in securities if r["symbol"] in symbols and r.get("cik")),
                key=lambda r: (seen.get(r["symbol"], ""), r["symbol"]),
            )[:10]
            payload = collect(store, [row["symbol"] for row in selected])
        elif job == "validate":
            from engine.validation import run as validate

            payload = validate(store, now)
        elif job == "history_sync":
            from engine.providers.daily_history import synchronize_many

            payload = synchronize_many(store, args.batches)
        elif job == "market_scan":
            from engine.market_scan import market_scan

            totals = {"claimed": 0, "covered": 0, "unavailable": 0, "failed": 0}
            for _ in range(args.batches):
                result = market_scan(store)
                for key in totals:
                    totals[key] += result.get(key, 0)
                if result["claimed"] and result.get("failed") == result["claimed"]:
                    raise RuntimeError(
                        "All history requests failed for this batch; collection stopped"
                    )
                if not result["claimed"]:
                    break
            payload = totals
            if totals["failed"]:
                payload["provider_errors"] = [
                    {
                        "provider": "Configured daily history",
                        "failed_symbols": totals["failed"],
                    }
                ]
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
                candidates = store.pages(
                    "latest_price_features", {"order": "symbol.asc"}
                )
                listed = store.pages(
                    "securities",
                    {
                        "select": "symbol,asset_type,listing_metadata",
                        "order": "symbol.asc",
                    },
                )
                contexts = store.pages(
                    "market_observations",
                    {
                        "select": "symbol,research_at:payload->>research_retrieved_at",
                        "feed": "in.(iex,finnhub_free)",
                        "payload->>research_retrieved_at": "not.is.null",
                        "order": "payload->>research_retrieved_at.desc,id.asc",
                    },
                )
                latest = {}
                for row in contexts:
                    latest.setdefault(row["symbol"], row["research_at"])
                from engine.discovery import select_candidates

                discovery = select_candidates(candidates, listed, latest, now)
                symbols = [row["symbol"] for row in discovery]
            else:
                discovery = [
                    {"symbol": symbol, "reasons": ["Explicit company research request"]}
                    for symbol in symbols
                ]
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
                "discovery": discovery,
                "discovery_policy": "measured-setup-priority-v1; not a prediction",
                "provider_errors": errors,
                "provider_failures": sum(
                    len(value["news"].get("errors", [])) for value in results.values()
                ),
            }
            # Newly discovered names need stored, sourced bars before their lines are scored.
            researched = list(results)
            if researched:
                from engine.fundamentals import collect

                payload["fundamentals"] = collect(store, researched)
                errors.extend(
                    {**error, "provider": "SEC fundamentals"}
                    for error in payload["fundamentals"]["provider_errors"]
                )
                try:
                    payload["price_collection"] = prices(
                        store, datetime.now(timezone.utc), researched
                    )
                except Exception as exc:
                    errors.append(
                        {"provider": "Nasdaq history", "error_type": type(exc).__name__}
                    )
                    from engine.history_cache import restore

                    payload["price_collection"] = {
                        "status": "unavailable",
                        "cached_history": restore(
                            store, researched, datetime.now(timezone.utc)
                        ),
                    }
                payload["scoring"] = score(
                    store, datetime.now(timezone.utc), researched
                )
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
        status = (
            "partial"
            if payload.get("provider_errors")
            or payload.get("provider_failures")
            or payload.get("continue_today")
            else "completed"
        )
    except Exception as exc:
        store.write(
            "engine_runs",
            [
                {
                    "id": f"{job}:{now.isoformat()}",
                    "job": job,
                    "as_of": now.isoformat(),
                    "status": "failed",
                    "payload": {
                        "error_type": type(exc).__name__,
                        "diagnostic": safe_diagnostic(exc),
                    },
                }
            ],
        )
        print(
            f"{job}: failed ({type(exc).__name__}; {safe_diagnostic(exc)}); cached data preserved"
        )
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
