"""Delivery performance summaries."""

import pandas as pd


def build_delivery_state_summary(order_level: pd.DataFrame) -> pd.DataFrame:
    delivered = order_level[order_level["order_status"].eq("delivered")]
    return (
        delivered.groupby("customer_state", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            average_delivery_days=("delivery_days", "mean"),
            late_delivery_rate=("late_delivery", "mean"),
            average_freight=("total_freight_value", "mean"),
            average_review=("average_review_score", "mean"),
        )
        .sort_values("late_delivery_rate", ascending=False)
    )
