from datetime import datetime, timedelta, timezone

import pytest

from engine.models import eligible_probability
from engine.validation import (
    capture,
    outcome,
    chronological_report,
    split_eligibility,
    HORIZON,
    calendar,
)

NOW = datetime(2026, 10, 8, 21, tzinfo=timezone.utc)


def fixture_case():
    return {
        "id": "fixture-case",
        "symbol": "FIXTURE",
        "as_of": NOW.isoformat(),
        "session_date": "2026-10-08",
        "payload": {
            "base_close": 100,
            "threshold": 0.05,
            "feed": "fixture-feed",
            "corporate_action_control": "unverified",
        },
    }


def test_five_session_outcome_does_not_grade_at_four_sessions():
    case = fixture_case()
    bars = [
        {
            "id": "fixture-observation",
            "feed": "fixture-feed",
            "session_date": "2026-10-15",
            "source": "fixture",
            "close": 110,
            "as_of": "2026-10-15T20:00:00+00:00",
            "available_at": "2026-10-15T21:00:00+00:00",
        }
    ]
    assert HORIZON == 5
    assert outcome(case, bars, datetime(2026, 10, 14, 21, tzinfo=timezone.utc)) is None
    result = outcome(case, bars, datetime(2026, 10, 15, 22, tzinfo=timezone.utc))
    assert result["payload"]["target_session"] == "2026-10-15"
    assert result["payload"]["label"] == 1
    assert result["payload"]["evaluation_eligible"] is False


def test_missing_target_session_cannot_be_replaced_by_later_price():
    case = fixture_case()
    assert outcome(case, [], datetime(2026, 10, 16, 22, tzinfo=timezone.utc)) is None


def test_future_cases_are_rejected_and_reports_cannot_approve_themselves():
    case = fixture_case()
    future = [
        {
            "id": case["id"],
            "evaluated_at": (NOW + timedelta(days=1)).isoformat(),
            "payload": {"evaluation_eligible": True},
        }
    ]
    with pytest.raises(ValueError):
        chronological_report([case], future, NOW)
    report = chronological_report([], [], NOW)
    assert report["status"] == "challenger"
    assert report["out_of_sample_n"] == 0
    assert not eligible_probability(
        report, report["line_kind"], report["horizon"], report["universe"]
    )


def test_no_forward_snapshot_before_the_close():
    assert (
        capture(None, datetime(2026, 10, 8, 16, tzinfo=timezone.utc))["snapshots"] == 0
    )


def test_split_control_requires_complete_known_reference():
    check = {
        "available_at": NOW.isoformat(),
        "payload": {
            "start": "2026-06-01",
            "end": "2026-10-08",
            "complete": True,
            "results": [],
        },
    }
    assert (
        split_eligibility([check], "FIXTURE", "2026-10-08", "2026-10-08", NOW)
        == "verified_no_splits"
    )
    check["payload"]["results"] = [
        {"ticker": "FIXTURE", "execution_date": "2026-10-07"}
    ]
    assert (
        split_eligibility([check], "FIXTURE", "2026-10-08", "2026-10-08", NOW)
        == "split_in_window"
    )
    check["available_at"] = (NOW + timedelta(seconds=1)).isoformat()
    with pytest.raises(ValueError):
        split_eligibility([check], "FIXTURE", "2026-10-08", "2026-10-08", NOW)


def test_chronological_evaluation_records_calibration_without_self_promotion():

    cal = calendar(NOW)
    sessions = list(cal.sessions_in_range("2026-01-02", "2026-04-30"))[:40]
    cases, results = [], []
    for index, session in enumerate(sessions):
        cutoff = cal.session_close(session).to_pydatetime() + timedelta(hours=1)
        target = cal.sessions_window(session, HORIZON + 1)[-1]
        for symbol in range(50):
            identity = f"fixture:{index}:{symbol}"
            cases.append(
                {
                    "id": identity,
                    "as_of": cutoff.isoformat(),
                    "session_date": session.date().isoformat(),
                    "payload": {
                        "feature_vector": [symbol % 2, index / 100],
                        "feature_as_of": cutoff.isoformat(),
                    },
                }
            )
            results.append(
                {
                    "id": identity,
                    "evaluated_at": (
                        cal.session_close(target).to_pydatetime() + timedelta(hours=1)
                    ).isoformat(),
                    "payload": {
                        "label": symbol % 2,
                        "target_session": target.date().isoformat(),
                        "evaluation_eligible": True,
                    },
                }
            )
    report = chronological_report(cases, results, NOW)
    assert report["out_of_sample_n"] == 250
    assert report["calibration_report"]["reliability"]
    assert report["uncertainty_estimate"]["method"] == "decision-date block bootstrap"
    assert report["train_end"] < report["calibration_start"] < report["test_start"]
    assert report["status"] == "challenger"
    assert report["probabilities_published"] is False


def test_snapshots_freeze_real_features_and_reject_unknown_feed():
    class Database:
        saved = []
        feed = "massive_daily_adjusted"
        gap = False

        def pages(self, table, params):
            if table == "securities":
                return [
                    {
                        "symbol": "FIXTURE",
                        "asset_type": "common_stock",
                        "listing_metadata": {"retrieved_at": NOW.isoformat()},
                    }
                ]
            return [
                {
                    "id": "fixture-features",
                    "symbol": "FIXTURE",
                    "version": "fixture-v1",
                    "as_of": NOW.isoformat(),
                    "observations": ["fixture-observation"],
                    "values": {
                        "feed": self.feed,
                        "sample_size": 80,
                        "source_window_61": [
                            s.date().isoformat()
                            for index, s in enumerate(
                                calendar(NOW).sessions_window("2026-10-08", -61)
                            )
                            if not self.gap or index != 10
                        ],
                        "last_close": 100,
                        "source_last_observed_at": "2026-10-08T20:00:00+00:00",
                        "adv_20": 10000000,
                        "rv_60": 0.3,
                        "return_20": 0.04,
                    },
                }
            ]

        def read(self, table, params):
            return [
                {
                    "available_at": NOW.isoformat(),
                    "payload": {
                        "complete": True,
                        "start": "2026-06-01",
                        "end": "2026-10-08",
                        "results": [],
                    },
                }
            ]

        def write(self, table, rows, immutable=False):
            assert table == "validation_cases" and immutable
            self.saved.extend(rows)

    database = Database()
    assert capture(database, NOW)["snapshots"] == 1
    assert database.saved[0]["payload"]["feature_values"]["last_close"] == 100
    assert database.saved[0]["payload"]["observation_ids"] == ["fixture-observation"]
    database.feed = "unverified_fixture_feed"
    assert capture(database, NOW)["snapshots"] == 0

    database.feed = "massive_daily_adjusted"
    database.gap = True
    assert capture(database, NOW)["snapshots"] == 0
