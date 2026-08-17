"""Retention and future-purchase analysis page."""

import plotly.express as px
import streamlit as st

from app.components.cards import metric_row
from app.components.charts import PRIMARY, style_figure
from app.components.helpers import format_percent, load_csv, load_parquet, load_results, page_header


def render() -> None:
    page_header("Retention Analysis", "Repeat purchasing, temporal future-purchase target, and cohort behavior")
    results = load_results()["retention"]
    customers = load_parquet("customer_features")
    metric_row(
        [
            ("Repeat Customer Rate", format_percent(customers["repeat_customer"].mean(), 2), "Uses customer_unique_id."),
            ("Observation Customers", f"{results['customers']:,}", None),
            ("Future Purchasers", f"{results['positive_count']:,}", None),
            ("Positive Class", format_percent(results["positive_rate"], 2), None),
            ("Model Trained", "Yes" if results["model_trained"] else "No", "A model is shown only when minimum class-size checks pass."),
        ]
    )
    st.info(
        f"Target: a customer observed by {results['observation_end'][:10]} purchases again between "
        f"{results['prediction_start'][:10]} and {results['prediction_end'][:10]}. The dataset has no native churn label."
    )
    if results["model_trained"]:
        metrics = load_csv("model_metrics")
        retention = metrics[metrics["module"].eq("Retention")].iloc[0]
        metric_row(
            [
                ("F1", f"{retention['f1']:.3f}", None),
                ("ROC-AUC", f"{retention['roc_auc']:.3f}", None),
                ("PR-AUC", f"{retention['pr_auc']:.3f}", "Compare with the 1.18% positive-class baseline."),
                ("Precision", f"{retention['precision']:.3f}", None),
                ("Recall", f"{retention['recall']:.3f}", None),
            ]
        )
        st.warning("The future-purchase target is sparse and the model's precision is low. Treat scores as exploratory ranking signals, not verified churn predictions.")
    left, right = st.columns(2)
    with left:
        capped = customers["recency"].clip(upper=customers["recency"].quantile(0.99))
        figure = px.histogram(x=capped, nbins=45, title="Customer Recency Distribution")
        figure.update_traces(marker_color=PRIMARY)
        figure.update_xaxes(title="Days since last observed purchase")
        st.plotly_chart(style_figure(figure), width="stretch")
    with right:
        frequency = customers["total_orders"].value_counts().sort_index().head(8).rename_axis("orders").rename("customers").reset_index()
        figure = px.bar(frequency, x="orders", y="customers", title="Returning Customer Behavior")
        figure.update_traces(marker_color="#00a6a6")
        st.plotly_chart(style_figure(figure), width="stretch")
    cohort = load_parquet("cohort_retention")
    cohort = cohort[cohort["cohort_size"].ge(100) & cohort["cohort_index"].le(12)]
    pivot = cohort.pivot(index="cohort_month", columns="cohort_index", values="retention_rate")
    figure = px.imshow(pivot, aspect="auto", color_continuous_scale="Blues", text_auto=".1%", title="Monthly Cohort Retention")
    figure.update_xaxes(title="Months since first purchase")
    st.plotly_chart(style_figure(figure, 520), width="stretch")
    st.caption("Limitations: a short marketplace history, sparse repeat behavior, and no inactivity-based ground-truth churn event constrain retention modelling.")
