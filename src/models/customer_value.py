"""Historical customer value outputs."""

import numpy as np
import pandas as pd


def build_historical_customer_value(customer_features: pd.DataFrame) -> pd.DataFrame:
    value = customer_features.copy()
    value["historical_customer_value"] = value["total_spend"]
    percentile = value["historical_customer_value"].rank(pct=True, method="average")
    value["value_tier"] = np.select(
        [percentile >= 0.95, percentile >= 0.75, percentile >= 0.40],
        ["Top 5%", "High Value", "Developing"],
        default="Low Value",
    )
    return value
