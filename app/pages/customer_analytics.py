"""Customer analytics page."""

import plotly.express as px
import streamlit as st

from app.components.cards import metric_row
from app.components.charts import ACCENT, PRIMARY, style_figure
from app.components.helpers import format_brl, format_percent, load_parquet, page_header


def render() -> None:
    page_header("Customer Analytics", "Durable customer identity, value, frequency, and geography")
    customers = load_parquet("customer_features")
    state = load_parquet("customer_state_summary")
    repeats = customers["repeat_customer"].sum()
    metric_row(
        [
            ("Unique Customers", f"{customers['customer_unique_id'].nunique():,}", "Uses customer_unique_id, not customer_id."),
            ("Repeat Customers", f"{int(repeats):,}", None),
            ("Repeat Customer Rate", format_percent(customers["repeat_customer"].mean(), 2), None),
            ("Average Customer Value", format_brl(customers["total_spend"].mean()), "Historical delivered merchandise spend."),
            ("Average Purchase Frequency", f"{customers['total_orders'].mean():.2f}", "Order identities per customer_unique_id."),
        ]
    )
    left, right = st.columns(2)
    with left:
        capped = customers["total_spend"].clip(upper=customers["total_spend"].quantile(0.99))
        figure = px.histogram(x=capped, nbins=45, title="Customer Spending Distribution (capped at 99th percentile)")
        figure.update_traces(marker_color=PRIMARY)
        figure.update_xaxes(title="Historical merchandise spend (R$)")
        st.plotly_chart(style_figure(figure), width="stretch")
    with right:
        frequency = customers["total_orders"].value_counts().sort_index().head(8).rename_axis("orders").rename("customers").reset_index()
        figure = px.bar(frequency, x="orders", y="customers", title="Purchase Frequency")
        figure.update_traces(marker_color=ACCENT)
        st.plotly_chart(style_figure(figure), width="stretch")
    top_states = state.head(15).sort_values("customers")
    figure = px.bar(top_states, x="customers", y="customer_state", orientation="h", color="customer_value", title="Customers and Historical Value by State", color_continuous_scale="Blues")
    st.plotly_chart(style_figure(figure, 450), width="stretch")
    st.subheader("Top Customer Segments")
    segment_counts = load_parquet("customer_segments")["segment"].value_counts().rename_axis("segment").rename("customers").reset_index()
    st.dataframe(segment_counts, width="stretch", hide_index=True)
