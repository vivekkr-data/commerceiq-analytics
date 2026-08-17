"""Delivery and satisfaction page."""

import plotly.express as px
import streamlit as st

from app.components.cards import metric_row
from app.components.charts import ACCENT, RISK, style_figure
from app.components.helpers import format_brl, format_percent, load_parquet, page_header


def render() -> None:
    page_header("Delivery & Satisfaction", "Logistics performance, review outcomes, and seller scorecards")
    delivery = load_parquet("delivery_analysis")
    delivered = delivery[delivery["delivery_days"].notna()]
    metric_row(
        [
            ("Average Delivery Days", f"{delivered['delivery_days'].mean():.1f}", None),
            ("Late Delivery Rate", format_percent(delivered["late_delivery"].mean()), None),
            ("Average Freight", format_brl(delivered["total_freight_value"].mean()), None),
            ("Average Review", f"{delivered['average_review_score'].mean():.2f}/5", None),
        ]
    )
    state = load_parquet("delivery_state_summary")
    left, right = st.columns(2)
    with left:
        chart = state.sort_values("average_delivery_days", ascending=False).head(15).sort_values("average_delivery_days")
        figure = px.bar(chart, x="average_delivery_days", y="customer_state", orientation="h", title="Delivery Time by State")
        figure.update_traces(marker_color=ACCENT)
        st.plotly_chart(style_figure(figure), width="stretch")
    with right:
        chart = state.sort_values("late_delivery_rate", ascending=False).head(15).sort_values("late_delivery_rate")
        figure = px.bar(chart, x="late_delivery_rate", y="customer_state", orientation="h", title="Late Delivery Rate by State")
        figure.update_traces(marker_color=RISK)
        figure.update_xaxes(tickformat=".0%")
        st.plotly_chart(style_figure(figure), width="stretch")
    left, right = st.columns(2)
    with left:
        reviews = load_parquet("review_distribution")
        figure = px.bar(reviews, x="review_score", y="orders", title="Review Score Distribution")
        figure.update_traces(marker_color="#1565c0")
        st.plotly_chart(style_figure(figure), width="stretch")
    with right:
        delay_review = load_parquet("delay_review_summary")
        figure = px.bar(delay_review, x="delivery_status", y="average_review", color="delivery_status", title="Delivery Timing vs Review Score")
        st.plotly_chart(style_figure(figure), width="stretch")
    st.caption("The review difference is an association in observational data and does not establish causation.")
    st.subheader("Seller Delivery Performance")
    sellers = load_parquet("seller_summary")
    minimum_orders = st.slider("Minimum delivered seller orders", 5, 100, 25)
    scorecard = sellers[sellers["orders"].ge(minimum_orders)].sort_values(
        ["late_delivery_rate", "average_review_score"], ascending=[True, False]
    ).head(30)
    st.dataframe(scorecard, width="stretch", hide_index=True)
