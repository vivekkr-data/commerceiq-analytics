"""Reusable model evaluation functions."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
    roc_auc_score,
)


def classification_metrics(y_true, y_pred, y_probability) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_probability)),
        "pr_auc": float(average_precision_score(y_true, y_probability)),
    }


def forecast_metrics(actual, predicted) -> dict[str, float]:
    actual_values = np.asarray(actual, dtype=float)
    predicted_values = np.asarray(predicted, dtype=float)
    nonzero = actual_values != 0
    mape = (
        float(np.mean(np.abs((actual_values[nonzero] - predicted_values[nonzero]) / actual_values[nonzero])))
        if nonzero.any()
        else np.nan
    )
    return {
        "mae": float(mean_absolute_error(actual_values, predicted_values)),
        "rmse": float(mean_squared_error(actual_values, predicted_values) ** 0.5),
        "mape": mape,
    }
