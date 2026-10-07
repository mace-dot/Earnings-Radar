"""Walk-forward logistic challenger; never self-promotes into public forecasts."""

from typing import Any

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def walk_forward(
    x: list[list[float]], labels: list[int], years: list[int]
) -> dict[str, Any]:
    if not len(x) == len(labels) == len(years) or not x:
        raise ValueError("Aligned historical feature rows required")
    array, y, calendar = np.asarray(x), np.asarray(labels), np.asarray(years)
    predicted, actual = [], []
    folds = []
    for year in sorted(set(years))[1:]:
        training, test = calendar < year, calendar == year
        if sum(training) < 30 or len(set(y[training])) < 2:
            continue
        model = make_pipeline(
            SimpleImputer(), StandardScaler(), LogisticRegression(C=0.5, max_iter=2000)
        )
        model.fit(array[training], y[training])
        probabilities = model.predict_proba(array[test])[:, 1]
        predicted.extend(probabilities.tolist())
        actual.extend(y[test].tolist())
        folds.append(
            {"test_year": year, "train_end_year": year - 1, "test_n": int(sum(test))}
        )
    if not actual:
        return {
            "status": "challenger",
            "out_of_sample_n": 0,
            "reason": "Insufficient untouched annual folds",
        }
    bins = []
    for lower in np.arange(0, 1, 0.1):
        mask = [
            (lower <= p < lower + 0.1) or (lower > 0.89 and p == 1) for p in predicted
        ]
        pairs = [(p, a) for p, a, selected in zip(predicted, actual, mask) if selected]
        bins.append(
            {
                "lower": round(float(lower), 1),
                "n": len(pairs),
                "predicted": float(np.mean([p for p, _ in pairs])) if pairs else None,
                "actual": float(np.mean([a for _, a in pairs])) if pairs else None,
            }
        )
    return {
        "status": "challenger",
        "out_of_sample_n": len(actual),
        "brier": brier_score_loss(actual, predicted),
        "log_loss": log_loss(actual, predicted, labels=[0, 1]),
        "reliability": bins,
        "folds": folds,
        "probabilities": predicted,
        "labels": actual,
        "baselines": {
            "always_bull_brier": brier_score_loss(actual, np.ones(len(actual))),
            "coinflip_brier": 0.25,
        },
        "promotion": "Separate untouched evaluation and approval required",
    }


def eligible_probability(
    registry: dict[str, Any], line_kind: str, horizon: str, universe: str
) -> bool:
    return bool(
        registry.get("status") == "validated"
        and registry.get("out_of_sample_n", 0) >= 200
        and registry.get("calibration_report")
        and registry.get("uncertainty_estimate")
        and registry.get("point_in_time_evaluation")
        and registry.get("untouched_evaluation")
        and registry.get("line_kind") == line_kind
        and registry.get("horizon") == horizon
        and registry.get("universe") == universe
    )


def magnitude_challenger(
    x: list[list[float]],
    absolute_moves: list[float],
    thresholds: list[float],
    years: list[int],
) -> dict[str, Any]:
    """Price-only research challenger with prior-year calibration and annual test folds.

    Thresholds must be known before each report. Targets are never interchangeable
    between trailing-median and option-implied comparisons. Missing data is not filled
    with future earnings information.
    """
    from sklearn.ensemble import (
        HistGradientBoostingClassifier,
        HistGradientBoostingRegressor,
    )
    from sklearn.metrics import roc_auc_score

    if not len(x) == len(absolute_moves) == len(thresholds) == len(years) or not x:
        raise ValueError("Aligned historical report rows required")
    features = np.asarray(x, dtype=float)
    moves = np.asarray(absolute_moves, dtype=float)
    limits = np.asarray(thresholds, dtype=float)
    calendar = np.asarray(years)
    if np.any(moves < 0) or np.any(limits <= 0) or not np.all(np.isfinite(moves)):
        raise ValueError("Real nonnegative moves and point-in-time thresholds required")
    labels = (moves > limits).astype(int)
    predicted, actual, quantiles, folds = [], [], [], []
    for year in sorted(set(years))[2:]:
        train = calendar < year - 1
        calibration = calendar == year - 1
        test = calendar == year
        if (
            sum(train) < 100
            or sum(calibration) < 50
            or len(set(labels[train])) < 2
            or len(set(labels[calibration])) < 2
        ):
            continue
        classifier = HistGradientBoostingClassifier(
            max_iter=80, max_leaf_nodes=15, l2_regularization=1, random_state=42
        )
        classifier.fit(features[train], labels[train])
        platt = LogisticRegression(C=1, max_iter=1000)
        platt.fit(
            classifier.decision_function(features[calibration]).reshape(-1, 1),
            labels[calibration],
        )
        probabilities = platt.predict_proba(
            classifier.decision_function(features[test]).reshape(-1, 1)
        )[:, 1]
        q_predictions = []
        for q in (0.5, 0.8):
            regression = HistGradientBoostingRegressor(
                loss="quantile",
                quantile=q,
                max_iter=80,
                max_leaf_nodes=15,
                l2_regularization=1,
                random_state=42,
            )
            regression.fit(features[train], moves[train])
            q_predictions.append(regression.predict(features[test]).tolist())
        predicted.extend(probabilities.tolist())
        actual.extend(labels[test].tolist())
        quantiles.extend(
            [
                {"median": max(0, float(a)), "p80": max(0, float(a), float(b))}
                for a, b in zip(*q_predictions)
            ]
        )
        folds.append(
            {
                "test_year": year,
                "calibration_year": year - 1,
                "train_end_year": year - 2,
                "test_n": int(sum(test)),
            }
        )
    if not actual:
        return {
            "status": "challenger",
            "out_of_sample_n": 0,
            "reason": "Historical train/calibration/test folds unavailable",
        }
    brier = float(brier_score_loss(actual, predicted))
    return {
        "status": "challenger",
        "out_of_sample_n": len(actual),
        "brier": brier,
        "auc": (
            float(roc_auc_score(actual, predicted)) if len(set(actual)) > 1 else None
        ),
        "always_more_brier": float(brier_score_loss(actual, np.ones(len(actual)))),
        "coinflip_brier": 0.25,
        "beats_coinflip": brier < 0.25,
        "folds": folds,
        "quantiles": quantiles,
        "probabilities": predicted,
        "labels": actual,
        "promotion": "Untouched validation required; no self-promotion",
    }
