"""Executive overview page."""

import plotly.express as px
import streamlit as st

from app.components.cards import metric_row
from app.components.charts import PRIMARY, style_figure
from app.components.filters import filter_orders
from app.components.helpers import download_csv, format_brl, format_percent, load_parquet, page_header
from src.analytics.insights import generate_filtered_business_insights


def render() -> None:
    page_header(
        "Executive Overview",
        "Sales • Customers • Segmentation • Delivery Risk • Retention • Forecasting",
    )
    orders = load_parquet("overview")
    filtered = filter_orders(orders, "overview")
    delivered = filtered[filtered["order_status"].eq("delivered")]
    if delivered.empty:
        st.info("No delivered orders match the selected filters.")
        return

    revenue = delivered["merchandise_revenue"].sum()
    order_count = delivered["order_id"].nunique()
    metric_row(
        [
            ("Merchandise Revenue", format_brl(revenue, compact=True), "Delivered item price only; freight excluded."),
            ("Delivered Orders", f"{order_count:,}", None),
            ("Unique Customers", f"{delivered['customer_unique_id'].nunique():,}", "Uses customer_unique_id."),
            ("Average Order Value", format_brl(revenue / order_count), None),
            ("Items Sold", f"{int(delivered['item_count'].sum()):,}", None),
            ("Late Delivery Rate", format_percent(delivered["late_delivery"].mean()), None),
        ]
    )

    monthly = (
        delivered.groupby("purchase_period", as_index=False)
        .agg(merchandise_revenue=("merchandise_revenue", "sum"), orders=("order_id", "nunique"))
    )
    left, right = st.columns(2)
    with left:
        figure = px.line(monthly, x="purchase_period", y="merchandise_revenue", markers=True, title="Revenue Trend")
        figure.update_traces(line_color=PRIMARY)
        st.plotly_chart(style_figure(figure), width="stretch")
    with right:
        figure = px.line(monthly, x="purchase_period", y="orders", markers=True, title="Orders Trend")
        figure.update_traces(line_color="#00a6a6")
        st.plotly_chart(style_figure(figure), width="stretch")

    category = (
        delivered.groupby("product_category", as_index=False)["merchandise_revenue"].sum()
        .nlargest(12, "merchandise_revenue").sort_values("merchandise_revenue")
    )
    state = (
        delivered.groupby("customer_state", as_index=False)["merchandise_revenue"].sum()
        .sort_values("merchandise_revenue")
    )
    left, right = st.columns(2)
    with left:
        figure = px.bar(category, x="merchandise_revenue", y="product_category", orientation="h", title="Revenue by Category")
        figure.update_traces(marker_color=PRIMARY)
        st.plotly_chart(style_figure(figure, 460), width="stretch")
    with right:
        figure = px.bar(state.tail(15), x="merchandise_revenue", y="customer_state", orientation="h", title="Revenue by Customer State")
        figure.update_traces(marker_color="#00a6a6")
        st.plotly_chart(style_figure(figure, 460), width="stretch")

    st.subheader("Key Business Insights")
    insights = generate_filtered_business_insights(filtered)
    for row in insights[:8]:
        st.markdown(
            f'<div class="insight-card"><strong>{row["theme"]}</strong><br>{row["insight"]}</div>',
            unsafe_allow_html=True,
        )
    download_csv(delivered, "Download filtered sales data", "filtered_sales.csv", "overview_download")
