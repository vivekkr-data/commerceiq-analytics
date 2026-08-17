"""Generate concise, computed business findings for reports and dashboard."""

from __future__ import annotations

import pandas as pd

from src.analytics.kpis import calculate_kpis


def generate_business_insights(
    order_level: pd.DataFrame,
    customer_features: pd.DataFrame,
    monthly_sales: pd.DataFrame,
    product_summary: pd.DataFrame,
    seller_summary: pd.DataFrame,
    state_sales: pd.DataFrame,
    payment_summary: pd.DataFrame,
    delay_review: pd.DataFrame,
) -> list[dict[str, str]]:
    kpis = calculate_kpis(order_level, customer_features)
    revenue = float(kpis["total_merchandise_revenue"])
    top_category = product_summary.iloc[0]
    top_state = state_sales.iloc[0]
    peak_month = monthly_sales.loc[monthly_sales["merchandise_revenue"].idxmax()]
    top_10_seller_share = seller_summary.head(10)["merchandise_revenue"].sum() / revenue
    primary_payment = payment_summary.iloc[0]
    delivered = order_level[order_level["order_status"].eq("delivered")]
    freight_ratio = delivered["total_freight_value"].sum() / revenue
    review_lookup = delay_review.set_index("delivery_status")["average_review"].to_dict()
    cancelled_unavailable = order_level["order_status"].isin(["canceled", "unavailable"]).sum()
    repeat_customers = int(customer_features["repeat_customer"].sum())

    return [
        {
            "theme": "Scale",
            "insight": f"Delivered merchandise revenue was R$ {revenue:,.2f} across {int(kpis['total_delivered_orders']):,} delivered orders.",
        },
        {
            "theme": "Category concentration",
            "insight": f"{top_category['product_category']} led categories with R$ {top_category['merchandise_revenue']:,.2f}, or {top_category['category_share']:.1%} of delivered merchandise revenue.",
        },
        {
            "theme": "Geography",
            "insight": f"{top_state['customer_state']} generated the most delivered merchandise revenue: R$ {top_state['merchandise_revenue']:,.2f} ({top_state['merchandise_revenue'] / revenue:.1%} of total).",
        },
        {
            "theme": "Customer retention",
            "insight": f"{repeat_customers:,} of {len(customer_features):,} unique customers placed more than one order identity, a {kpis['repeat_customer_rate']:.2%} repeat-customer rate.",
        },
        {
            "theme": "Delivery risk",
            "insight": f"{kpis['late_delivery_rate']:.2%} of delivered orders with valid delivery dates arrived after the estimate.",
        },
        {
            "theme": "Satisfaction",
            "insight": f"Average review score was {kpis['average_review_score']:.2f}/5; on-time orders averaged {review_lookup.get('On time or early', float('nan')):.2f} versus {review_lookup.get('Late', float('nan')):.2f} for late orders. This is associative, not causal.",
        },
        {
            "theme": "Freight",
            "insight": f"Delivered freight totaled {freight_ratio:.1%} of merchandise revenue, highlighting logistics as a material part of order value.",
        },
        {
            "theme": "Payments",
            "insight": f"{primary_payment['dominant_payment_type'].replace('_', ' ').title()} was the dominant method for {int(primary_payment['orders']):,} delivered orders.",
        },
        {
            "theme": "Seasonality",
            "insight": f"The highest complete-month revenue occurred in {peak_month['purchase_period']:%B %Y} at R$ {peak_month['merchandise_revenue']:,.2f}.",
        },
        {
            "theme": "Seller concentration",
            "insight": f"The top 10 sellers contributed {top_10_seller_share:.1%} of delivered merchandise revenue.",
        },
        {
            "theme": "Order outcomes",
            "insight": f"{cancelled_unavailable:,} orders were canceled or unavailable ({kpis['cancellation_rate']:.2%} of all orders).",
        },
        {
            "theme": "Delivery duration",
            "insight": f"Average delivery time for delivered orders was {kpis['average_delivery_days']:.1f} days.",
        },
    ]
