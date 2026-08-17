"""Shared test fixtures."""

import pandas as pd
import pytest


@pytest.fixture
def sample_order_level() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3", "o4"],
            "customer_unique_id": ["c1", "c1", "c2", "c3"],
            "order_status": ["delivered", "delivered", "canceled", "unavailable"],
            "merchandise_revenue": [100.0, 50.0, 80.0, 20.0],
            "item_count": [2, 1, 1, 1],
            "average_review_score": [5.0, 3.0, None, None],
            "delivery_days": [10.0, 20.0, None, None],
            "late_delivery": pd.Series([0, 1, pd.NA, pd.NA], dtype="Int64"),
        }
    )


@pytest.fixture
def sample_customer_features() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer_unique_id": ["c1", "c2", "c3"],
            "repeat_customer": [True, False, False],
        }
    )
