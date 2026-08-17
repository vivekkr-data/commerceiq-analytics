"""Customer analytical summaries."""

import pandas as pd


def build_customer_state_summary(customer_features: pd.DataFrame) -> pd.DataFrame:
    return (
        customer_features.groupby("customer_state", as_index=False)
        .agg(
            customers=("customer_unique_id", "nunique"),
            repeat_customers=("repeat_customer", "sum"),
            customer_value=("total_spend", "sum"),
            average_order_value=("average_order_value", "mean"),
        )
        .assign(repeat_customer_rate=lambda frame: frame["repeat_customers"] / frame["customers"])
        .sort_values("customers", ascending=False)
    )
