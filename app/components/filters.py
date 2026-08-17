"""Shared dashboard filters."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def filter_orders(data: pd.DataFrame, key_prefix: str) -> pd.DataFrame:
    dates = pd.to_datetime(data["order_purchase_timestamp"])
    minimum, maximum = dates.min().date(), dates.max().date()
    selected_dates = st.sidebar.date_input(
        "Purchase date",
        value=(minimum, maximum),
        min_value=minimum,
        max_value=maximum,
        key=f"{key_prefix}_dates",
    )
    states = sorted(data["customer_state"].dropna().unique().tolist())
    selected_states = st.sidebar.multiselect(
        "Customer state",
        states,
        default=[],
        placeholder="All states",
        help="Leave blank to include every customer state.",
        key=f"{key_prefix}_states",
    )
    categories = sorted(data["product_category"].dropna().unique().tolist())
    selected_categories = st.sidebar.multiselect(
        "Primary category",
        categories,
        default=[],
        placeholder="All categories",
        help="Leave blank to include every product category.",
        key=f"{key_prefix}_categories",
    )
    filtered = data.copy()
    if selected_states:
        filtered = filtered[filtered["customer_state"].isin(selected_states)]
    if selected_categories:
        filtered = filtered[filtered["product_category"].isin(selected_categories)]
    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start, end = pd.Timestamp(selected_dates[0]), pd.Timestamp(selected_dates[1]) + pd.Timedelta(days=1)
        filtered = filtered[
            filtered["order_purchase_timestamp"].ge(start)
            & filtered["order_purchase_timestamp"].lt(end)
        ]
    return filtered
