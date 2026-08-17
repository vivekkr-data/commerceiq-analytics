"""Product analytics helpers."""

import pandas as pd


def top_categories(product_summary: pd.DataFrame, count: int = 10) -> pd.DataFrame:
    return product_summary.nlargest(count, "merchandise_revenue").copy()
