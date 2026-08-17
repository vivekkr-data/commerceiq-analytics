"""Leakage-safe late-delivery risk classification."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, precision_recall_curve, roc_curve
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

from src.config import DELIVERY_MODEL_FEATURES, POST_OUTCOME_COLUMNS, RANDOM_STATE
from src.data.validate_data import assert_columns_excluded
from src.models.evaluation import classification_metrics


def build_delivery_training_data(
    order_level: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    assert_columns_excluded(DELIVERY_MODEL_FEATURES, POST_OUTCOME_COLUMNS)
    delivered = order_level[
        order_level["order_status"].eq("delivered") & order_level["late_delivery"].notna()
    ].sort_values("order_purchase_timestamp").copy()
    features = delivered[DELIVERY_MODEL_FEATURES].copy()
    target = delivered["late_delivery"].astype(int)
    identifiers = delivered[
        ["order_id", "order_purchase_timestamp", "customer_state", "late_delivery"]
    ].copy()
    return features, target, identifiers


def _preprocessor(features: pd.DataFrame) -> tuple[ColumnTransformer, list[str], list[str]]:
    categorical = features.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    numeric = [column for column in features.columns if column not in categorical]
    preprocessing = ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore", min_frequency=20)),
                    ]
                ),
                categorical,
            ),
        ]
    )
    return preprocessing, numeric, categorical


def _extract_feature_importance(model: Pipeline) -> pd.DataFrame:
    names = model.named_steps["preprocessing"].get_feature_names_out()
    estimator = model.named_steps["model"]
    if hasattr(estimator, "feature_importances_"):
        values = estimator.feature_importances_
    elif hasattr(estimator, "coef_"):
        values = np.abs(estimator.coef_[0])
    else:
        return pd.DataFrame(columns=["feature", "importance"])
    return (
        pd.DataFrame({"feature": names, "importance": values})
        .sort_values("importance", ascending=False)
        .head(30)
    )


def train_delivery_model(
    order_level: pd.DataFrame,
    model_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    features, target, identifiers = build_delivery_training_data(order_level)
    split_index = int(len(features) * 0.80)
    x_train, x_test = features.iloc[:split_index], features.iloc[split_index:]
    y_train, y_test = target.iloc[:split_index], target.iloc[split_index:]

    candidates = {
        "Dummy Baseline": DummyClassifier(strategy="prior"),
        "Logistic Regression": LogisticRegression(
            max_iter=1_000, class_weight="balanced", random_state=RANDOM_STATE
        ),
        "Decision Tree": DecisionTreeClassifier(
            max_depth=9, min_samples_leaf=40, class_weight="balanced", random_state=RANDOM_STATE
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=160,
            max_depth=18,
            min_samples_leaf=5,
            class_weight="balanced_subsample",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
    }
    results: list[dict[str, object]] = []
    fitted: dict[str, Pipeline] = {}
    test_probabilities: dict[str, np.ndarray] = {}
    for name, estimator in candidates.items():
        preprocessing, _, _ = _preprocessor(features)
        pipeline = Pipeline([("preprocessing", preprocessing), ("model", estimator)])
        pipeline.fit(x_train, y_train)
        probability = pipeline.predict_proba(x_test)[:, 1]
        prediction = (probability >= 0.5).astype(int)
        results.append({"model": name, **classification_metrics(y_test, prediction, probability)})
        fitted[name] = pipeline
        test_probabilities[name] = probability

    comparison = pd.DataFrame(results)
    eligible = comparison[~comparison["model"].eq("Dummy Baseline")]
    selected_name = str(eligible.sort_values(["f1", "pr_auc"], ascending=False).iloc[0]["model"])
    comparison["selected"] = comparison["model"].eq(selected_name)
    selected_model = fitted[selected_name]
    selected_probability = test_probabilities[selected_name]
    selected_prediction = (selected_probability >= 0.5).astype(int)
    matrix = confusion_matrix(y_test, selected_prediction)
    confusion = pd.DataFrame(
        matrix,
        index=["Actual on time", "Actual late"],
        columns=["Predicted on time", "Predicted late"],
    ).reset_index(names="actual")
    false_positive_rate, true_positive_rate, roc_thresholds = roc_curve(y_test, selected_probability)
    roc_data = pd.DataFrame(
        {
            "false_positive_rate": false_positive_rate,
            "true_positive_rate": true_positive_rate,
            "threshold": roc_thresholds,
        }
    )
    precision_values, recall_values, pr_thresholds = precision_recall_curve(
        y_test, selected_probability
    )
    pr_data = pd.DataFrame(
        {
            "precision": precision_values,
            "recall": recall_values,
            "threshold": np.append(pr_thresholds, np.nan),
        }
    )

    all_probability = selected_model.predict_proba(features)[:, 1]
    predictions = identifiers.copy()
    predictions["late_delivery_probability"] = all_probability
    predictions["risk_category"] = pd.cut(
        predictions["late_delivery_probability"],
        bins=[-np.inf, 0.25, 0.50, np.inf],
        labels=["Low", "Medium", "High"],
    ).astype(str)
    predictions["evaluation_split"] = np.where(
        np.arange(len(predictions)) < split_index, "Training", "Chronological test"
    )
    importance = _extract_feature_importance(selected_model)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": selected_model, "features": DELIVERY_MODEL_FEATURES, "threshold": 0.5},
        model_path,
    )
    selected_metrics = comparison.loc[comparison["selected"]].iloc[0].to_dict()
    metadata = {
        "selected_model": selected_name,
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "test_start": str(identifiers.iloc[split_index]["order_purchase_timestamp"]),
        "positive_rate_train": float(y_train.mean()),
        "positive_rate_test": float(y_test.mean()),
        "metrics": selected_metrics,
        "confusion_matrix": matrix.tolist(),
    }
    return comparison, predictions, importance, {
        "metadata": metadata,
        "confusion": confusion,
        "roc_curve": roc_data,
        "pr_curve": pr_data,
    }
