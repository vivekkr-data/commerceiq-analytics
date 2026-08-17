"""KPI definition tests."""

import pytest

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
