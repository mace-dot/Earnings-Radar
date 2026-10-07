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
