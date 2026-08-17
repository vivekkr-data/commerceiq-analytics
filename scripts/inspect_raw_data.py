"""Profile the raw Olist CSV files before pipeline development."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

EXPECTED_KEYS = {
    "customers": [["customer_id"]],
    "orders": [["order_id"]],
    "order_items": [["order_id", "order_item_id"]],
    "payments": [["order_id", "payment_sequential"]],
    "reviews": [["review_id"], ["order_id"], ["review_id", "order_id"]],
    "products": [["product_id"]],
    "sellers": [["seller_id"]],
    "geolocation": [["geolocation_zip_code_prefix"]],
    "category_translation": [["product_category_name"]],
}


def scalar(value: object) -> object:
    if pd.isna(value):
        return None
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def profile_table(name: str, path: Path) -> dict[str, object]:
    data = pd.read_csv(path, low_memory=False)
    rows = len(data)
    null_counts = data.isna().sum()
    unique_counts = data.nunique(dropna=True)

    dates: dict[str, dict[str, object]] = {}
    for column in data.columns:
        if "date" in column or "timestamp" in column:
            parsed = pd.to_datetime(data[column], errors="coerce")
            dates[column] = {
                "valid": int(parsed.notna().sum()),
                "invalid_non_null": int((data[column].notna() & parsed.isna()).sum()),
                "minimum": scalar(parsed.min()),
                "maximum": scalar(parsed.max()),
            }

    numeric: dict[str, dict[str, object]] = {}
    for column in data.select_dtypes(include="number").columns:
        values = data[column]
        numeric[column] = {
            "minimum": scalar(values.min()),
            "maximum": scalar(values.max()),
            "zero_count": int((values == 0).sum()),
            "negative_count": int((values < 0).sum()),
            "non_finite_count": int((~np.isfinite(values.dropna())).sum()),
        }

    categories: dict[str, dict[str, object]] = {}
    for column in data.select_dtypes(include=["object", "string"]).columns:
        counts = data[column].value_counts(dropna=False).head(10)
        categories[column] = {
            "unique": int(unique_counts[column]),
            "top_values": {str(scalar(key)): int(value) for key, value in counts.items()},
            "leading_or_trailing_whitespace": int(
                data[column].dropna().astype(str).str.strip().ne(data[column].dropna().astype(str)).sum()
            ),
        }

    key_checks: list[dict[str, object]] = []
    for columns in EXPECTED_KEYS[name]:
        if all(column in data.columns for column in columns):
            missing = int(data[columns].isna().any(axis=1).sum())
            duplicates = int(data.duplicated(columns, keep=False).sum())
            key_checks.append(
                {
                    "columns": columns,
                    "missing_rows": missing,
                    "duplicate_rows": duplicates,
                    "is_candidate_key": missing == 0 and duplicates == 0,
                }
            )

    return {
        "file": path.name,
        "rows": rows,
        "columns": len(data.columns),
        "column_names": data.columns.tolist(),
        "dtypes": {column: str(dtype) for column, dtype in data.dtypes.items()},
        "null_counts": {column: int(value) for column, value in null_counts.items()},
        "null_percentages": {
            column: round(float(value / rows * 100), 4) if rows else 0.0
            for column, value in null_counts.items()
        },
        "duplicate_rows": int(data.duplicated().sum()),
        "unique_counts": {column: int(value) for column, value in unique_counts.items()},
        "candidate_key_checks": key_checks,
        "date_ranges": dates,
        "numeric_checks": numeric,
        "categorical_summaries": categories,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    profiles = {
        name: profile_table(name, args.raw_dir / filename)
        for name, filename in FILES.items()
    }
    result = {"tables": profiles}

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = {
        name: {
            "shape": [profile["rows"], profile["columns"]],
            "columns": profile["column_names"],
            "dtypes": profile["dtypes"],
            "null_counts": profile["null_counts"],
            "duplicate_rows": profile["duplicate_rows"],
            "candidate_key_checks": profile["candidate_key_checks"],
            "date_ranges": profile["date_ranges"],
            "numeric_checks": profile["numeric_checks"],
        }
        for name, profile in profiles.items()
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
