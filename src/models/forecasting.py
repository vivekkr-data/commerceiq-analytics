"""Monthly merchandise-revenue forecasting with partial-tail detection."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from src.models.evaluation import forecast_metrics


def detect_complete_months(monthly_sales: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = monthly_sales.sort_values("purchase_period").reset_index(drop=True)
    order_signal = "all_orders" if "all_orders" in ordered.columns else "orders"
    cutoff_index = len(ordered) - 1
    while cutoff_index >= 6:
        previous_median = ordered.loc[cutoff_index - 6 : cutoff_index - 1, order_signal].median()
        if ordered.loc[cutoff_index, order_signal] >= max(50, previous_median * 0.25):
            break
        cutoff_index -= 1
    complete = ordered.iloc[: cutoff_index + 1].copy()
    partial = ordered.iloc[cutoff_index + 1 :].copy()
    return complete, partial


def _trend_features(periods: pd.Series | pd.DatetimeIndex, start_index: int = 0) -> np.ndarray:
    dates = pd.DatetimeIndex(periods)
    index = np.arange(start_index, start_index + len(dates))
    return np.column_stack(
        [index, np.sin(2 * np.pi * dates.month / 12), np.cos(2 * np.pi * dates.month / 12)]
    )


def _validation_predictions(name: str, train: pd.Series, test: pd.Series, test_dates: pd.Series) -> np.ndarray:
    history = train.astype(float).tolist()
    predictions: list[float] = []
    if name == "Linear Trend + Seasonality":
        model = LinearRegression().fit(
            _trend_features(pd.date_range("2000-01-01", periods=len(train), freq="MS")),
            train,
        )
        fake_dates = pd.date_range("2000-01-01", periods=len(train) + len(test), freq="MS")[-len(test):]
        return np.maximum(model.predict(_trend_features(fake_dates, len(train))), 0)
    for actual in test:
        if name == "Last Value Naive":
            prediction = history[-1]
        elif name == "Moving Average (3)":
            prediction = float(np.mean(history[-3:]))
        elif name == "Seasonal Naive":
            prediction = history[-12] if len(history) >= 12 else history[-1]
        else:
            raise ValueError(name)
        predictions.append(prediction)
        history.append(float(actual))
    return np.asarray(predictions)


def _future_predictions(
    name: str, values: pd.Series, periods: pd.Series, future_dates: pd.DatetimeIndex
) -> np.ndarray:
    history = values.astype(float).tolist()
    predictions: list[float] = []
    if name == "Linear Trend + Seasonality":
        model = LinearRegression().fit(_trend_features(periods), values)
        return np.maximum(model.predict(_trend_features(future_dates, len(values))), 0)
    for _ in future_dates:
        if name == "Last Value Naive":
            prediction = history[-1]
        elif name == "Moving Average (3)":
            prediction = float(np.mean(history[-3:]))
        elif name == "Seasonal Naive":
            prediction = history[-12] if len(history) >= 12 else history[-1]
        else:
            raise ValueError(name)
        predictions.append(prediction)
        history.append(prediction)
    return np.asarray(predictions)


def train_forecast_models(
    monthly_sales: pd.DataFrame,
    model_path: Path,
    future_horizon: int = 6,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    complete, partial = detect_complete_months(monthly_sales)
    validation_months = min(4, max(3, len(complete) // 5))
    train = complete.iloc[:-validation_months]
    test = complete.iloc[-validation_months:]
    candidates = ["Last Value Naive", "Moving Average (3)", "Seasonal Naive", "Linear Trend + Seasonality"]
    rows: list[dict[str, object]] = []
    predictions: dict[str, np.ndarray] = {}
    for name in candidates:
        predicted = _validation_predictions(
            name,
            train["merchandise_revenue"],
            test["merchandise_revenue"],
            test["purchase_period"],
        )
        predictions[name] = predicted
        rows.append({"model": name, **forecast_metrics(test["merchandise_revenue"], predicted)})
    comparison = pd.DataFrame(rows)
    selected_name = str(comparison.sort_values("rmse").iloc[0]["model"])
    comparison["selected"] = comparison["model"].eq(selected_name)

    cutoff = pd.Timestamp(complete["purchase_period"].max())
    future_dates = pd.date_range(cutoff + pd.offsets.MonthBegin(1), periods=future_horizon, freq="MS")
    future_values = _future_predictions(
        selected_name,
        complete["merchandise_revenue"],
        complete["purchase_period"],
        future_dates,
    )
    history = complete[["purchase_period", "merchandise_revenue"]].rename(
        columns={"merchandise_revenue": "actual"}
    )
    history["predicted"] = np.nan
    history["future_forecast"] = np.nan
    history["split"] = "Training"
    validation_indices = history.tail(validation_months).index
    history.loc[validation_indices, "predicted"] = predictions[selected_name]
    history.loc[validation_indices, "split"] = "Validation"
    future = pd.DataFrame(
        {
            "purchase_period": future_dates,
            "actual": np.nan,
            "predicted": np.nan,
            "future_forecast": future_values,
            "split": "Future Forecast",
        }
    )
    if not partial.empty:
        excluded = partial[["purchase_period", "merchandise_revenue"]].rename(
            columns={"merchandise_revenue": "actual"}
        )
        excluded["predicted"] = np.nan
        excluded["future_forecast"] = np.nan
        excluded["split"] = "Excluded Partial"
        history = pd.concat([history, excluded], ignore_index=True)
    forecast_history = pd.concat([history, future], ignore_index=True).sort_values("purchase_period")

    bundle = {
        "selected_model": selected_name,
        "complete_history": complete[["purchase_period", "merchandise_revenue"]],
        "future_horizon": future_horizon,
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path)
    metadata = {
        "selected_model": selected_name,
        "complete_cutoff": str(cutoff.date()),
        "excluded_partial_months": [str(value.date()) for value in partial["purchase_period"]],
        "train_start": str(train["purchase_period"].min().date()),
        "train_end": str(train["purchase_period"].max().date()),
        "validation_start": str(test["purchase_period"].min().date()),
        "validation_end": str(test["purchase_period"].max().date()),
        "metrics": comparison.loc[comparison["selected"]].iloc[0].to_dict(),
    }
    return comparison, forecast_history, metadata
