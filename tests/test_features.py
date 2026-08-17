"""Processed feature and grain tests."""

import pandas as pd

from src.config import CORE_DIR, DASHBOARD_DIR
from src.models.segmentation import create_rfm_features


def test_processed_order_level_is_unique():
    data = pd.read_parquet(CORE_DIR / "order_level.parquet", columns=["order_id"])
    assert len(data) == 99_441
    assert data["order_id"].is_unique


def test_processed_customer_level_is_unique():
    data = pd.read_parquet(DASHBOARD_DIR / "customer_features.parquet", columns=["customer_unique_id"])
    assert len(data) == 96_096
    assert data["customer_unique_id"].is_unique


def test_processed_zip_summary_is_unique():
    data = pd.read_parquet(CORE_DIR / "geolocation_zip_summary.parquet")
    assert data["geolocation_zip_code_prefix"].is_unique
    assert len(data) == 19_015


def test_rfm_excludes_customers_without_delivered_purchase():
    customers = pd.DataFrame(
        {
            "customer_unique_id": ["a", "b"], "recency": [1, 2],
            "frequency": [1, 0], "monetary": [10.0, 0.0], "delivered_orders": [1, 0],
        }
    )
    result = create_rfm_features(customers)
    assert result["customer_unique_id"].tolist() == ["a"]


def test_monthly_sales_marks_partial_tail():
    data = pd.read_parquet(DASHBOARD_DIR / "monthly_sales.parquet")
    partial = data[~data["is_complete"]]
    assert partial["purchase_period"].dt.strftime("%Y-%m").tolist() == ["2018-09", "2018-10"]


def test_dashboard_artifacts_are_present():
    expected = [
        "overview.parquet", "monthly_sales.parquet", "customer_segments.parquet",
        "delivery_predictions.parquet", "forecast_history.parquet", "product_summary.parquet",
        "seller_summary.parquet", "model_metrics.csv",
    ]
    assert all((DASHBOARD_DIR / name).exists() for name in expected)
