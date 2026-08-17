"""Sales-oriented analytical summaries."""

import pandas as pd


def build_state_sales(order_level: pd.DataFrame) -> pd.DataFrame:
    delivered = order_level[order_level["order_status"].eq("delivered")]
    return (
        delivered.groupby("customer_state", as_index=False)
        .agg(
            merchandise_revenue=("merchandise_revenue", "sum"),
            orders=("order_id", "nunique"),
            customers=("customer_unique_id", "nunique"),
            average_order_value=("merchandise_revenue", "mean"),
        )
        .sort_values("merchandise_revenue", ascending=False)
    )


def build_payment_summary(order_level: pd.DataFrame) -> pd.DataFrame:
    delivered = order_level[order_level["order_status"].eq("delivered")]
    return (
        delivered.groupby("dominant_payment_type", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            amount_paid=("total_payment_value", "sum"),
            average_installments=("maximum_installments", "mean"),
        )
        .sort_values("orders", ascending=False)
    )
