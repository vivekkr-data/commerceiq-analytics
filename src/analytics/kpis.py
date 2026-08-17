"""Canonical KPI definitions used by Python, SQL, dashboard, and tests."""

from __future__ import annotations

import pandas as pd


def delivered_orders(order_level: pd.DataFrame) -> pd.DataFrame:
    return order_level[order_level["order_status"].eq("delivered")]


def total_merchandise_revenue(order_level: pd.DataFrame) -> float:
    return float(delivered_orders(order_level)["merchandise_revenue"].sum())


def total_delivered_orders(order_level: pd.DataFrame) -> int:
    return int(delivered_orders(order_level)["order_id"].nunique())


def unique_customers(order_level: pd.DataFrame) -> int:
    return int(delivered_orders(order_level)["customer_unique_id"].nunique())


def average_order_value(order_level: pd.DataFrame) -> float:
    orders = total_delivered_orders(order_level)
    return total_merchandise_revenue(order_level) / orders if orders else 0.0


def items_sold(order_level: pd.DataFrame) -> int:
    return int(delivered_orders(order_level)["item_count"].sum())


def average_review_score(order_level: pd.DataFrame) -> float:
    return float(delivered_orders(order_level)["average_review_score"].mean())


def average_delivery_days(order_level: pd.DataFrame) -> float:
    return float(delivered_orders(order_level)["delivery_days"].mean())


def late_delivery_rate(order_level: pd.DataFrame) -> float:
    return float(delivered_orders(order_level)["late_delivery"].mean())


def repeat_customer_rate(customer_features: pd.DataFrame) -> float:
    return float(customer_features["repeat_customer"].mean())


def cancellation_rate(order_level: pd.DataFrame) -> float:
    return float(order_level["order_status"].isin(["canceled", "unavailable"]).mean())


def calculate_kpis(
    order_level: pd.DataFrame, customer_features: pd.DataFrame
) -> dict[str, float | int]:
    return {
        "total_merchandise_revenue": total_merchandise_revenue(order_level),
        "total_delivered_orders": total_delivered_orders(order_level),
        "unique_customers": unique_customers(order_level),
        "average_order_value": average_order_value(order_level),
        "items_sold": items_sold(order_level),
        "average_review_score": average_review_score(order_level),
        "average_delivery_days": average_delivery_days(order_level),
        "late_delivery_rate": late_delivery_rate(order_level),
        "repeat_customer_rate": repeat_customer_rate(customer_features),
        "cancellation_rate": cancellation_rate(order_level),
    }
