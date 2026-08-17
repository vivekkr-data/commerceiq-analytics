"""Sales forecasting page."""

import plotly.graph_objects as go
import streamlit as st

from app.components.cards import metric_row
from app.components.charts import ACCENT, PRIMARY, style_figure
from app.components.helpers import format_brl, load_csv, load_parquet, load_results, page_header


def render() -> None:
    page_header("Sales Forecast", "Chronological validation, incomplete-tail handling, and a conservative six-month horizon")
    results = load_results()["forecast"]
    metrics = load_csv("model_metrics")
    selected = metrics[
        metrics["module"].eq("Forecasting")
        & metrics["selected"].astype(str).str.lower().eq("true")
    ].iloc[0]
    model_display = {
        "Last Value Naive": "Naive (last)",
        "Moving Average (3)": "3-month average",
        "Seasonal Naive": "Seasonal naive",
        "Linear Trend + Seasonality": "Trend + seasonality",
    }.get(str(selected["model"]), str(selected["model"]))
    metric_row(
        [
            ("Selected Model", model_display, None),
            ("MAE", format_brl(selected["mae"]), None),
            ("RMSE", format_brl(selected["rmse"]), None),
            ("MAPE", f"{selected['mape']:.1%}", None),
            ("Complete Cutoff", results["complete_cutoff"], "Sparse September/October 2018 raw tail is excluded."),
        ]
    )
    st.caption(
        f"Training: {results['train_start']} to {results['train_end']} • Validation: "
        f"{results['validation_start']} to {results['validation_end']} • Future horizon: 6 months."
    )
    history = load_parquet("forecast_history").sort_values("purchase_period")
    figure = go.Figure()
    actual = history[history["actual"].notna() & ~history["split"].eq("Excluded Partial")]
    validation = history[history["predicted"].notna()]
    future = history[history["future_forecast"].notna()]
    excluded = history[history["split"].eq("Excluded Partial")]
    figure.add_scatter(x=actual["purchase_period"], y=actual["actual"], mode="lines+markers", name="Actual", line=dict(color=PRIMARY))
    figure.add_scatter(x=validation["purchase_period"], y=validation["predicted"], mode="lines+markers", name="Predicted", line=dict(color="#f59e0b"))
    figure.add_scatter(x=future["purchase_period"], y=future["future_forecast"], mode="lines+markers", name="Future Forecast", line=dict(color=ACCENT, dash="dash"))
    if not excluded.empty:
        figure.add_scatter(x=excluded["purchase_period"], y=excluded["actual"], mode="markers", name="Excluded Partial", marker=dict(color="#94a3b8", symbol="x", size=10))
    figure.update_layout(title="Actual, Validation Prediction, and Future Forecast", yaxis_title="Merchandise revenue (R$)")
    st.plotly_chart(style_figure(figure, 500), width="stretch")
    st.subheader("Forecasting Model Comparison")
    comparison = metrics[metrics["module"].eq("Forecasting")][["model", "mae", "rmse", "mape", "selected"]]
    st.dataframe(comparison, width="stretch", hide_index=True)
    st.info("Why this model was selected: it achieved the lowest chronological validation RMSE. Forecasts are scenarios based on historical monthly sales, not guaranteed future revenue.")
