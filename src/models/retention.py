"""Temporal future-purchase feasibility analysis and optional model."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.config import RANDOM_STATE
from src.models.evaluation import classification_metrics


RETENTION_FEATURES = [
    "orders_before_cutoff", "spend_before_cutoff", "items_before_cutoff",
    "average_order_value", "recency_at_cutoff", "tenure_at_cutoff",
    "average_freight", "average_review", "late_delivery_rate",
]


def build_temporal_retention_dataset(
    order_level: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, dict[str, str]]:
    delivered = order_level[order_level["order_status"].eq("delivered")].copy()
    prediction_end = pd.Timestamp("2018-08-31 23:59:59")
    prediction_start = pd.Timestamp("2018-03-01")
    observation_end = prediction_start - pd.Timedelta(seconds=1)
    observed = delivered[delivered["order_purchase_timestamp"].le(observation_end)].copy()
    future_customers = set(
        delivered.loc[
            delivered["order_purchase_timestamp"].between(prediction_start, prediction_end),
            "customer_unique_id",
        ]
    )
    features = (
        observed.groupby("customer_unique_id", as_index=False)
        .agg(
            orders_before_cutoff=("order_id", "nunique"),
            spend_before_cutoff=("merchandise_revenue", "sum"),
            items_before_cutoff=("item_count", "sum"),
            first_purchase=("order_purchase_timestamp", "min"),
            last_purchase=("order_purchase_timestamp", "max"),
            average_freight=("total_freight_value", "mean"),
            average_review=("average_review_score", "mean"),
            late_delivery_rate=("late_delivery", "mean"),
        )
    )
    features["average_order_value"] = features["spend_before_cutoff"] / features["orders_before_cutoff"]
    features["recency_at_cutoff"] = (prediction_start - features["last_purchase"]).dt.days
    features["tenure_at_cutoff"] = (features["last_purchase"] - features["first_purchase"]).dt.days
    target = features["customer_unique_id"].isin(future_customers).astype(int)
    windows = {
        "observation_start": str(observed["order_purchase_timestamp"].min()),
        "observation_end": str(observation_end),
        "prediction_start": str(prediction_start),
        "prediction_end": str(prediction_end),
    }
    return features, target, windows


def evaluate_retention_feasibility(
    order_level: pd.DataFrame,
    model_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    features, target, windows = build_temporal_retention_dataset(order_level)
    positives = int(target.sum())
    positive_rate = float(target.mean())
    defensible = positives >= 200 and positive_rate >= 0.005 and int((target == 0).sum()) >= 1_000
    metadata: dict[str, object] = {
        **windows,
        "customers": int(len(target)),
        "positive_count": positives,
        "negative_count": int((target == 0).sum()),
        "positive_rate": positive_rate,
        "model_trained": defensible,
    }
    predictions = features[["customer_unique_id", *RETENTION_FEATURES]].copy()
    if not defensible:
        predictions["future_purchase_probability"] = np.nan
        metrics = pd.DataFrame(
            [{"model": "Not trained", "reason": "Future-purchase target was too sparse for responsible modelling"}]
        )
        return metrics, predictions, metadata

    x_train, x_test, y_train, y_test = train_test_split(
        features[RETENTION_FEATURES],
        target,
        test_size=0.25,
        stratify=target,
        random_state=RANDOM_STATE,
    )
    pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(class_weight="balanced", max_iter=1_000, random_state=RANDOM_STATE)),
        ]
    )
    pipeline.fit(x_train, y_train)
    probability = pipeline.predict_proba(x_test)[:, 1]
    prediction = (probability >= 0.5).astype(int)
    values = classification_metrics(y_test, prediction, probability)
    metrics = pd.DataFrame([{"model": "Logistic Regression", **values, "selected": True}])
    predictions["future_purchase_probability"] = pipeline.predict_proba(
        features[RETENTION_FEATURES]
    )[:, 1]
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": pipeline, "features": RETENTION_FEATURES, "windows": windows}, model_path)
    metadata["metrics"] = values
    metadata["train_rows"] = int(len(x_train))
    metadata["test_rows"] = int(len(x_test))
    return metrics, predictions, metadata
