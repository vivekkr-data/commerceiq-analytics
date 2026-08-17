"""KPI definition tests."""

import pytest
import pandas as pd

from src.analytics.insights import generate_filtered_business_insights
from src.analytics.kpis import (
    average_delivery_days,
    average_order_value,
    average_review_score,
    cancellation_rate,
    items_sold,
    late_delivery_rate,
    repeat_customer_rate,
    total_delivered_orders,
    total_merchandise_revenue,
    unique_customers,
)


def test_total_merchandise_revenue_uses_delivered_only(sample_order_level):
    assert total_merchandise_revenue(sample_order_level) == 150.0


def test_total_delivered_orders(sample_order_level):
    assert total_delivered_orders(sample_order_level) == 2


def test_unique_customer_count_uses_durable_id(sample_order_level):
    assert unique_customers(sample_order_level) == 1


def test_average_order_value(sample_order_level):
    assert average_order_value(sample_order_level) == 75.0


def test_items_sold(sample_order_level):
    assert items_sold(sample_order_level) == 3


def test_average_review(sample_order_level):
    assert average_review_score(sample_order_level) == 4.0


def test_average_delivery_days(sample_order_level):
    assert average_delivery_days(sample_order_level) == 15.0


def test_late_delivery_rate(sample_order_level):
    assert late_delivery_rate(sample_order_level) == 0.5


def test_repeat_customer_rate(sample_customer_features):
    assert repeat_customer_rate(sample_customer_features) == pytest.approx(1 / 3)


def test_cancellation_rate_includes_unavailable(sample_order_level):
    assert cancellation_rate(sample_order_level) == 0.5


def test_filtered_business_insights_use_only_selected_orders():
    selected = pd.DataFrame(
        {
            "order_id": ["o1", "o2", "o3"],
            "customer_unique_id": ["c1", "c1", "c2"],
            "order_status": ["delivered", "delivered", "canceled"],
            "merchandise_revenue": [100.0, 50.0, 999.0],
            "product_category": ["Art", "Air Conditioning", "Other"],
            "customer_state": ["AM", "AM", "SP"],
            "late_delivery": pd.Series([0, 1, pd.NA], dtype="Int64"),
            "average_review_score": [5.0, 3.0, None],
            "total_freight_value": [10.0, 5.0, 100.0],
            "dominant_payment_type": ["credit_card", "credit_card", "voucher"],
        }
    )

    insights = generate_filtered_business_insights(selected)
    by_theme = {row["theme"]: row["insight"] for row in insights}

    assert "R$ 150.00 across 2 delivered orders" in by_theme["Scale"]
    assert "Art was the leading primary category" in by_theme["Primary category concentration"]
    assert "AM generated the most" in by_theme["Geography"]
    assert "1 of 1 unique customers" in by_theme["Customer retention"]
    assert "Credit Card" in by_theme["Payments"]
