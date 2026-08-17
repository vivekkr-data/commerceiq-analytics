"""Review and satisfaction summaries."""

import pandas as pd


def build_review_distribution(order_level: pd.DataFrame) -> pd.DataFrame:
    delivered = order_level[order_level["order_status"].eq("delivered")]
    distribution = (
        delivered["review_score"].dropna().astype(int).value_counts().sort_index()
        .rename_axis("review_score").rename("orders").reset_index()
    )
    return distribution


def build_delay_review_summary(order_level: pd.DataFrame) -> pd.DataFrame:
    delivered = order_level[
        order_level["order_status"].eq("delivered") & order_level["review_score"].notna()
    ].copy()
    delivered["delivery_status"] = delivered["late_delivery"].map(
        {0: "On time or early", 1: "Late"}
    )
    return (
        delivered.groupby("delivery_status", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            average_review=("review_score", "mean"),
            average_delay_days=("delivery_delay_days", "mean"),
        )
    )
