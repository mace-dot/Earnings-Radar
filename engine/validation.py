"""Prospective, immutable model evaluation; no reconstructed availability or self-approval."""

from datetime import datetime, timedelta
from math import erfc, sqrt
from typing import Any

import exchange_calendars as xcals
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

VERSION = "forward-price-magnitude-v1"
THRESHOLD = 0.05
HORIZON = 5
KEYS = ("return_5", "return_20", "rv_10", "rv_60", "vol_compression_ratio")


def calendar(now: datetime) -> Any:
    return xcals.get_calendar(
        "XNYS", start=f"{now.year-1}-01-01", end=f"{now.year+1}-12-31"
    )


def capture(store: Any, now: datetime, limit: int = 500) -> dict[str, Any]:
    cal = calendar(now)
    today = now.astimezone(cal.tz).date().isoformat()
    if not cal.is_session(today) or cal.session_close(today) > now:
        return {
            "snapshots": 0,
            "reason": "Forward cases are frozen only after the exchange close",
        }
    features = store.pages(
        "latest_price_features",
        {
            "select": "id,symbol,as_of,values,observations,version",
            "order": "symbol.asc",
        },
    )
    identities = {
        r["symbol"]: r
        for r in store.pages(
            "securities",
            {"select": "symbol,asset_type,listing_metadata", "order": "symbol.asc"},
        )
    }
    checks = store.read(
        "market_history_days",
        {"feed": "eq.massive_splits_120d", "order": "session_date.desc", "limit": "1"},
    )
    output = []
    # Rotate the bounded research cohort rather than always selecting A-tickers.
    if features:
        start = now.date().toordinal() * limit % len(features)
        features = features[start:] + features[:start]
    for row in features:
        f, identity = row["values"], identities.get(row["symbol"], {})
        observed = f.get("source_last_observed_at")
        listing_at = identity.get("listing_metadata", {}).get("retrieved_at")
        if (
            not observed
            or not listing_at
            or identity.get("asset_type") != "common_stock"
        ):
            continue
        as_of = datetime.fromisoformat(row["as_of"])
        observation_time = datetime.fromisoformat(observed)
        listing_time = datetime.fromisoformat(listing_at)
        if max(as_of, observation_time, listing_time) > now:
            raise ValueError("Future feature or identity cannot enter validation")
        if observation_time.astimezone(cal.tz).date().isoformat() != today:
            continue
        if (
            f.get("feed") != "massive_daily_adjusted"
            or split_eligibility(checks, row["symbol"], today, today, now)
            != "verified_no_splits"
        ):
            continue
        expected_sessions = [
            s.date().isoformat() for s in cal.sessions_window(today, -61)
        ]
        if f.get("source_window_61") != expected_sessions:
            continue
        if now - listing_time > timedelta(days=7) or f.get("sample_size", 0) < 61:
            continue
        if (f.get("last_close") or 0) < 5 or (f.get("adv_20") or 0) < 5000000:
            continue
        rv = f.get("rv_60")
        sigma = rv * sqrt(HORIZON / 252) if rv and rv > 0 else None
        output.append(
            {
                "id": f"{row['symbol']}:{today}:{VERSION}",
                "symbol": row["symbol"],
                "as_of": now.isoformat(),
                "session_date": today,
                "version": VERSION,
                "payload": {
                    "horizon_sessions": HORIZON,
                    "threshold": THRESHOLD,
                    "target": "Absolute sourced close-to-close stock change over five future exchange sessions exceeds 5%; not option profit",
                    "base_close": f["last_close"],
                    "feature_keys": list(KEYS),
                    "feature_vector": [f.get(key) for key in KEYS],
                    "feature_id": row["id"],
                    "feature_as_of": row["as_of"],
                    "feature_version": row["version"],
                    "feature_values": f,
                    "feed": f.get("feed"),
                    "observation_ids": row.get("observations", []),
                    "source_last_observed_at": observed,
                    "listing_metadata": identity["listing_metadata"],
                    "gaussian_reference": (
                        erfc(THRESHOLD / (sigma * sqrt(2))) if sigma else None
                    ),
                    "reference_status": "Unvalidated zero-drift Gaussian benchmark, not a published forecast",
                    "corporate_action_control": split_eligibility(
                        checks, row["symbol"], today, today, now
                    ),
                },
            }
        )
        if len(output) == limit:
            break
    for offset in range(0, len(output), 100):
        store.write("validation_cases", output[offset : offset + 100], immutable=True)
    return {
        "snapshots": len(output),
        "version": VERSION,
        "probabilities_published": False,
    }


def outcome(
    case: dict[str, Any],
    bars: list[dict[str, Any]],
    now: datetime,
    checks: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    cutoff = datetime.fromisoformat(case["as_of"])
    if cutoff > now:
        raise ValueError("Future decision cannot be evaluated")
    cal = calendar(cutoff)
    sessions = cal.sessions_window(case["session_date"], HORIZON + 1)
    target = sessions[-1].date().isoformat()
    if cal.session_close(target) > now:
        return None
    matching = [b for b in bars if str(b["session_date"]) == target]
    eligible = [
        b
        for b in matching
        if b["feed"] == case["payload"].get("feed")
        and datetime.fromisoformat(b["available_at"]) <= now
        and datetime.fromisoformat(b["as_of"]) <= now
    ]
    if not eligible:
        return None
    # Choose one source deterministically, never stitch or select a favorable outcome.
    chosen = sorted(
        eligible,
        key=lambda b: (
            b["source"] != "Massive",
            b["source"] != "Nasdaq",
            b["available_at"],
        ),
    )[0]
    control = split_eligibility(
        checks or [], case["symbol"], case["session_date"], target, now
    )
    ready = (
        control == "verified_no_splits"
        and case["payload"]["corporate_action_control"] == "verified_no_splits"
        and case["payload"].get("feed") == "massive_daily_adjusted"
    )
    absolute = abs(chosen["close"] / case["payload"]["base_close"] - 1)
    return {
        "id": case["id"],
        "evaluated_at": now.isoformat(),
        "payload": {
            "target_session": target,
            "absolute_move": absolute,
            "label": int(absolute > case["payload"]["threshold"]),
            "close": chosen["close"],
            "observation_id": chosen["id"],
            "source": chosen["source"],
            "source_as_of": chosen["as_of"],
            "source_available_at": chosen["available_at"],
            "corporate_action_control": control,
            "evaluation_eligible": ready,
            "blocked_reasons": (
                []
                if ready
                else [
                    "Verified same-feed history and split-free feature/outcome windows are required"
                ]
            ),
        },
    }


def chronological_report(
    cases: list[dict[str, Any]], outcomes: list[dict[str, Any]], now: datetime
) -> dict[str, Any]:
    indexed = {r["id"]: r for r in outcomes}
    usable = []
    blocked = 0
    for case in cases:
        if case["id"] not in indexed:
            continue
        result = indexed[case["id"]]
        for timestamp in ("feature_as_of", "source_last_observed_at"):
            value = case["payload"].get(timestamp)
            if value and datetime.fromisoformat(value) > datetime.fromisoformat(
                case["as_of"]
            ):
                raise ValueError("Feature was unavailable when the decision was frozen")
        if (
            max(
                datetime.fromisoformat(case["as_of"]),
                datetime.fromisoformat(result["evaluated_at"]),
            )
            > now
        ):
            raise ValueError("Future outcomes cannot enter an evaluation")
        if not result["payload"].get("evaluation_eligible"):
            blocked += 1
            continue
        usable.append((case, result))
    dates = sorted({c["session_date"] for c, _ in usable})
    base = {
        "status": "challenger",
        "version": VERSION,
        "line_kind": "stock_move_5_sessions",
        "horizon": "5_exchange_sessions",
        "threshold": THRESHOLD,
        "universe": "liquid_US_common_equities",
        "frozen_cases": len(cases),
        "labeled_cases": len(indexed),
        "eligible_cases": len(usable),
        "blocked_corporate_action_cases": blocked,
        "out_of_sample_n": 0,
        "as_of": now.isoformat(),
        "probabilities_published": False,
        "promotion": "Independent review required; this job cannot approve itself",
    }
    if len(dates) < 30:
        return {
            **base,
            "reason": "At least 30 distinct completed decision sessions and 200 untouched test cases are required",
        }
    calibration_start, test_start = dates[-15], dates[-5]
    calibration_cutoff = min(
        datetime.fromisoformat(c["as_of"])
        for c, _ in usable
        if c["session_date"] >= calibration_start
    )
    test_cutoff = min(
        datetime.fromisoformat(c["as_of"])
        for c, _ in usable
        if c["session_date"] >= test_start
    )
    train = [
        (c, o)
        for c, o in usable
        if c["session_date"] < calibration_start
        and o["payload"]["target_session"] < calibration_start
        and datetime.fromisoformat(o["evaluated_at"]) < calibration_cutoff
    ]
    calibrate = [
        (c, o)
        for c, o in usable
        if calibration_start <= c["session_date"] < test_start
        and o["payload"]["target_session"] < test_start
        and datetime.fromisoformat(o["evaluated_at"]) < test_cutoff
    ]
    test = [(c, o) for c, o in usable if c["session_date"] >= test_start]

    def y(rows):
        return [o["payload"]["label"] for _, o in rows]

    if (
        len(train) < 100
        or len(calibrate) < 50
        or len(test) < 200
        or min(len(set(y(train))), len(set(y(calibrate)))) < 2
    ):
        return {
            **base,
            "reason": "Train/calibration/untouched-test coverage is insufficient",
        }

    def x(rows):
        return [
            [np.nan if v is None else v for v in c["payload"]["feature_vector"]]
            for c, _ in rows
        ]

    model = make_pipeline(
        SimpleImputer(), StandardScaler(), LogisticRegression(C=0.5, max_iter=2000)
    )
    model.fit(x(train), y(train))
    platt = LogisticRegression(C=1, max_iter=1000)
    platt.fit(model.decision_function(x(calibrate)).reshape(-1, 1), y(calibrate))
    probabilities = platt.predict_proba(
        model.decision_function(x(test)).reshape(-1, 1)
    )[:, 1]
    actual = np.asarray(y(test))
    reliability = []
    for lower in np.arange(0, 1, 0.1):
        mask = (probabilities >= lower) & (probabilities < lower + 0.1)
        reliability.append(
            {
                "lower": round(float(lower), 1),
                "n": int(mask.sum()),
                "predicted": float(probabilities[mask].mean()) if mask.any() else None,
                "actual": float(actual[mask].mean()) if mask.any() else None,
            }
        )
    # Resample complete decision dates so correlated stocks are not treated as independent.
    losses = {
        day: [
            (p - a) ** 2
            for p, a, (c, _) in zip(probabilities, actual, test)
            if c["session_date"] == day
        ]
        for day in sorted({c["session_date"] for c, _ in test})
    }
    values = list(losses.values())
    generator = np.random.default_rng(42)
    draws = [
        float(
            np.mean(
                [
                    loss
                    for index in generator.integers(0, len(values), len(values))
                    for loss in values[index]
                ]
            )
        )
        for _ in range(500)
    ]
    return {
        **base,
        "out_of_sample_n": len(test),
        "point_in_time_evaluation": True,
        "untouched_evaluation": True,
        "brier": float(brier_score_loss(actual, probabilities)),
        "calibration_report": {
            "reliability": reliability,
            "calibration_cases": len(calibrate),
        },
        "uncertainty_estimate": {
            "method": "decision-date block bootstrap",
            "brier_95_interval": np.quantile(draws, [0.025, 0.975]).tolist(),
        },
        "baselines": {
            "training_base_rate_brier": float(
                brier_score_loss(actual, np.full(len(actual), np.mean(y(train))))
            )
        },
        "train_end": max(c["session_date"] for c, _ in train),
        "calibration_start": calibration_start,
        "test_start": test_start,
        "test_case_ids": [c["id"] for c, _ in test],
    }


def run(store: Any, now: datetime) -> dict[str, Any]:
    frozen = capture(store, now)
    cases = store.pages(
        "validation_cases",
        {"version": f"eq.{VERSION}", "order": "as_of.asc,id.asc"},
        capacity=100000,
    )
    outcomes = store.pages(
        "validation_outcomes", {"order": "evaluated_at.asc,id.asc"}, capacity=100000
    )
    completed = {r["id"] for r in outcomes}
    cal = calendar(now)
    pending = [
        c
        for c in cases
        if c["id"] not in completed
        and cal.session_close(cal.sessions_window(c["session_date"], HORIZON + 1)[-1])
        <= now
    ]
    checks = store.read(
        "market_history_days",
        {"feed": "eq.massive_splits_120d", "order": "session_date.desc", "limit": "1"},
    )
    new = []
    for offset in range(0, len(pending), 100):
        batch = pending[offset : offset + 100]
        symbols = sorted({c["symbol"] for c in batch})
        bars = store.pages(
            "daily_bars",
            {
                "symbol": "in.(" + ",".join(symbols) + ")",
                "order": "symbol.asc,session_date.asc",
                "session_date": "gte." + min(c["session_date"] for c in batch),
            },
            capacity=100000,
        )
        adjusted_symbols = sorted(
            {
                c["symbol"]
                for c in batch
                if c["payload"].get("feed") == "massive_daily_adjusted"
            }
        )
        if adjusted_symbols:
            archived = store.rpc(
                "radar_history_bars",
                {
                    "p_symbols": adjusted_symbols,
                    "p_start": min(c["session_date"] for c in batch),
                    "p_end": now.date().isoformat(),
                },
            )
            bars.extend(
                {
                    **row,
                    "id": f"{row['symbol']}:{row['session_date']}:{row['feed']}",
                    "as_of": row["observed_at"],
                }
                for row in archived
            )
        for case in batch:
            result = outcome(
                case, [b for b in bars if b["symbol"] == case["symbol"]], now, checks
            )
            if result:
                new.append(result)
    for offset in range(0, len(new), 100):
        store.write("validation_outcomes", new[offset : offset + 100], immutable=True)
    report = chronological_report(cases, outcomes + new, now)
    store.write(
        "model_registry",
        [
            {
                "id": f"{VERSION}:{now.isoformat()}",
                "line_kind": report["line_kind"],
                "trained_at": now.isoformat(),
                "status": "challenger",
                "payload": report,
            }
        ],
        immutable=True,
    )
    return {**frozen, "new_outcomes": len(new), "report": report}


def split_eligibility(
    checks: list[dict[str, Any]], symbol: str, start: str, end: str, now: datetime
) -> str:
    required_start = (
        (datetime.fromisoformat(start) - timedelta(days=100)).date().isoformat()
    )
    for check in checks:
        if datetime.fromisoformat(check["available_at"]) > now:
            raise ValueError("Future corporate-action check")
        p = check["payload"]
        if not p.get("complete") or p["start"] > required_start or p["end"] < end:
            continue
        if any(
            r.get("ticker") == symbol and required_start <= r["execution_date"] <= end
            for r in p["results"]
        ):
            return "split_in_window"
        return "verified_no_splits"
    return "unverified"
