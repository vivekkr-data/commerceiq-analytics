"""Sales analytics page."""

import plotly.express as px
import streamlit as st

from app.components.cards import metric_row
from app.components.charts import ACCENT, PRIMARY, style_figure
from app.components.helpers import download_csv, format_brl, load_parquet, page_header


def render() -> None:
    page_header("Sales Analytics", "Delivered merchandise performance, growth, geography, and payments")
    monthly = load_parquet("monthly_sales")
    complete = monthly[monthly["is_complete"]].copy()
    state = load_parquet("state_sales")
    payment = load_parquet("payment_summary")
    metric_row(
        [
            ("Complete Months", f"{len(complete)}", "Sparse September/October 2018 tail is excluded."),
            ("Peak Monthly Revenue", format_brl(complete["merchandise_revenue"].max(), compact=True), None),
            ("Latest Complete Revenue", format_brl(complete.iloc[-1]["merchandise_revenue"], compact=True), None),
            ("Latest Complete Orders", f"{int(complete.iloc[-1]['orders']):,}", None),
        ]
    )
    figure = px.line(
        complete,
        x="purchase_period",
        y="merchandise_revenue",
        markers=True,
        title="Monthly Delivered Merchandise Revenue",
    )
    figure.update_traces(line_color=PRIMARY)
    st.plotly_chart(style_figure(figure, 430), width="stretch")
    left, right = st.columns(2)
    with left:
        growth = complete.dropna(subset=["revenue_growth"]).copy()
        figure = px.bar(growth, x="purchase_period", y="revenue_growth", title="Month-over-Month Revenue Growth")
        figure.update_traces(marker_color=ACCENT)
        figure.update_yaxes(tickformat=".0%")
        st.plotly_chart(style_figure(figure), width="stretch")
    with right:
        top_state = state.head(12).sort_values("merchandise_revenue")
        figure = px.bar(top_state, x="merchandise_revenue", y="customer_state", orientation="h", title="Top States by Revenue")
        figure.update_traces(marker_color=PRIMARY)
        st.plotly_chart(style_figure(figure), width="stretch")
    figure = px.bar(
        payment,
        x="dominant_payment_type",
        y="orders",
        color="average_installments",
        title="Dominant Payment Method and Average Installments",
        color_continuous_scale="Blues",
    )
    st.plotly_chart(style_figure(figure), width="stretch")
    download_csv(complete, "Download monthly sales", "monthly_sales.csv", "sales_download")
