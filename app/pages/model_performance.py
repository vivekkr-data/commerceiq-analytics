"""Consolidated model performance page."""

import streamlit as st

from app.components.helpers import download_csv, load_csv, load_parquet, load_results, page_header


def render() -> None:
    page_header("Model Performance", "Comparable evaluation evidence and honest model-selection rationale")
    metrics = load_csv("model_metrics")
    st.subheader("Delivery Risk Model Comparison")
    delivery = metrics[metrics["module"].eq("Delivery Risk")][
        ["model", "accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "selected"]
    ]
    st.dataframe(delivery, width="stretch", hide_index=True)
    st.info("Why selected: the Decision Tree produced the strongest chronological-test F1 among trained candidates, while the baseline's high accuracy came from predicting the majority class.")

    st.subheader("Forecasting Model Comparison")
    forecast = metrics[metrics["module"].eq("Forecasting")][["model", "mae", "rmse", "mape", "selected"]]
    st.dataframe(forecast, width="stretch", hide_index=True)
    st.info("Why selected: Last Value Naive had the lowest RMSE across the four-month chronological validation window, outperforming more complex alternatives on this short history.")

    st.subheader("Segmentation Evaluation")
    segmentation = metrics[metrics["module"].eq("Segmentation")][["clusters", "inertia", "silhouette", "selected"]]
    st.dataframe(segmentation, width="stretch", hide_index=True)
    st.info("Why selected: K=2 achieved the strongest Silhouette Score and produced two interpretable engagement/value profiles. Extra clusters reduced separation.")

    st.subheader("Retention Model")
    retention = metrics[metrics["module"].eq("Retention")]
    st.dataframe(retention, width="stretch", hide_index=True)
    results = load_results()["retention"]
    st.warning(
        f"Only {results['positive_count']:,} of {results['customers']:,} observation customers purchased in the future window. "
        "The model is retained as a transparent feasibility experiment, not a production churn system."
    )
    download_csv(metrics, "Download model comparison data", "model_metrics.csv", "model_download")
