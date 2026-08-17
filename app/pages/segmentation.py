"""Customer segmentation page."""

import plotly.express as px
import streamlit as st

from app.components.cards import metric_row
from app.components.charts import style_figure
from app.components.helpers import download_csv, format_brl, load_csv, load_parquet, load_results, page_header


INTERPRETATIONS = {
    "Champions": ("Most recent, frequent, and valuable customers.", "Protect loyalty with early access and recognition."),
    "High Value": ("Customers with stronger frequency and spend than the broader base.", "Prioritize loyalty offers and relevant cross-sell."),
    "Loyal": ("Repeat customers with consistent value.", "Use replenishment and category-affinity campaigns."),
    "Regular": ("Mid-value customers with ordinary purchase patterns.", "Encourage a second or next purchase with targeted offers."),
    "At Risk": ("Customers whose recency is weaker relative to their value.", "Test selective re-engagement based on prior category."),
    "Low Engagement": ("Mostly one-order customers with lower historical engagement.", "Use low-cost onboarding and post-purchase journeys."),
    "Dormant": ("Long-recency, low-frequency customers.", "Limit spend and use measured win-back tests."),
}


def render() -> None:
    page_header("Customer Segmentation", "RFM profiles selected with Silhouette Score and business interpretability")
    summary = load_parquet("segment_summary")
    segments = load_parquet("customer_segments")
    metrics = load_csv("model_metrics")
    results = load_results()["segmentation"]
    metric_row(
        [
            ("Selected Clusters", str(results["selected_k"]), None),
            ("Silhouette Score", f"{results['silhouette']:.3f}", None),
            ("Customers Segmented", f"{results['customers_segmented']:,}", None),
            ("Largest Segment", str(summary.loc[summary["customers"].idxmax(), "segment"]), None),
        ]
    )
    left, right = st.columns(2)
    with left:
        figure = px.bar(
            summary.sort_values("customers"),
            x="customers", y="segment", orientation="h", color="monetary",
            title="Segment Sizes", color_continuous_scale="Blues",
        )
        st.plotly_chart(style_figure(figure), width="stretch")
    with right:
        figure = px.scatter(
            summary,
            x="recency", y="monetary", size="customers", color="segment",
            hover_data=["frequency"], title="RFM Segment Profile",
        )
        st.plotly_chart(style_figure(figure), width="stretch")
    display = summary[["segment", "customers", "recency", "frequency", "monetary"]].copy()
    display.columns = ["Segment", "Customers", "Avg Recency (days)", "Avg Frequency", "Avg Monetary (R$)"]
    st.subheader("Segment Comparison")
    st.dataframe(display, width="stretch", hide_index=True)
    st.subheader("Segment Interpretation")
    interpretation_rows = []
    for segment in summary["segment"]:
        description, action = INTERPRETATIONS.get(segment, ("Observed RFM cluster.", "Validate messaging with controlled tests."))
        interpretation_rows.append({"Segment": segment, "Customer behaviour": description, "Potential business action": action})
    st.dataframe(interpretation_rows, width="stretch", hide_index=True)
    st.subheader("K Selection Evidence")
    k_metrics = metrics[metrics["module"].eq("Segmentation")][["clusters", "inertia", "silhouette", "selected"]]
    st.dataframe(k_metrics, width="stretch", hide_index=True)
    download_csv(segments, "Download customer segments", "customer_segments.csv", "segment_download")
