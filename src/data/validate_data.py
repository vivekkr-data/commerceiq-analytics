"""Data contracts and duplicate-safe validation checks."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from src.config import EXPECTED_ROW_COUNTS, EXPECTED_SCHEMAS


def validate_required_schemas(tables: dict[str, pd.DataFrame]) -> None:
    for name, required_columns in EXPECTED_SCHEMAS.items():
        missing = sorted(set(required_columns) - set(tables[name].columns))
        if missing:
            raise ValueError(f"{name} is missing columns: {missing}")


def assert_unique_key(data: pd.DataFrame, columns: list[str], table_name: str) -> None:
    if data[columns].isna().any(axis=None):
        raise AssertionError(f"{table_name} key {columns} contains nulls")
    if data.duplicated(columns).any():
        raise AssertionError(f"{table_name} key {columns} is not unique")


def assert_no_row_multiplication(before: pd.DataFrame, after: pd.DataFrame, grain: str) -> None:
    if len(after) != len(before):
        raise AssertionError(f"Join changed {grain} row count from {len(before):,} to {len(after):,}")


def assert_columns_excluded(features: Iterable[str], forbidden: Iterable[str]) -> None:
    overlap = sorted(set(features) & set(forbidden))
    if overlap:
        raise AssertionError(f"Model features contain leakage columns: {overlap}")


def validate_raw_keys(tables: dict[str, pd.DataFrame]) -> dict[str, object]:
    assert_unique_key(tables["customers"], ["customer_id"], "customers")
    assert_unique_key(tables["orders"], ["order_id"], "orders")
    assert_unique_key(tables["products"], ["product_id"], "products")
    assert_unique_key(tables["sellers"], ["seller_id"], "sellers")
    assert_unique_key(tables["order_items"], ["order_id", "order_item_id"], "order_items")
    assert_unique_key(tables["payments"], ["order_id", "payment_sequential"], "payments")
    assert_unique_key(tables["reviews"], ["review_id", "order_id"], "reviews")

    return {
        "review_id_is_unique": not tables["reviews"].duplicated("review_id").any(),
        "review_order_id_is_unique": not tables["reviews"].duplicated("order_id").any(),
        "geolocation_zip_is_unique": not tables["geolocation"].duplicated(
            "geolocation_zip_code_prefix"
        ).any(),
    }


def build_validation_report(tables: dict[str, pd.DataFrame]) -> dict[str, object]:
    validate_required_schemas(tables)
    key_findings = validate_raw_keys(tables)
    report: dict[str, object] = {"tables": {}, "key_findings": key_findings}
    for name, data in tables.items():
        expected = EXPECTED_ROW_COUNTS[name]
        report["tables"][name] = {
            "rows": int(len(data)),
            "columns": int(len(data.columns)),
            "expected_rows": expected,
            "row_count_matches_reference": len(data) == expected,
            "duplicate_rows": int(data.duplicated().sum()),
            "null_cells": int(data.isna().sum().sum()),
        }

    orders = tables["orders"]
    report["purchase_date_min"] = str(orders["order_purchase_timestamp"].min())
    report["purchase_date_max"] = str(orders["order_purchase_timestamp"].max())
    report["unique_customer_ids"] = int(tables["customers"]["customer_unique_id"].nunique())
    report["repeat_identity_count"] = int(
        (tables["customers"]["customer_unique_id"].value_counts() > 1).sum()
    )
    return report
