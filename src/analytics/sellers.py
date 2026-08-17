"""Seller analytics helpers."""

import pandas as pd


def top_sellers(seller_summary: pd.DataFrame, count: int = 10) -> pd.DataFrame:
    return seller_summary.nlargest(count, "merchandise_revenue").copy()
