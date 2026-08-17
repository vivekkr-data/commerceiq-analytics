"""Raw contracts and grain-safe ETL tests."""

import numpy as np
import pandas as pd

from src.config import EXPECTED_ROW_COUNTS, EXPECTED_SCHEMAS, RAW_FILES
from src.data.clean_data import clean_products, parse_date_columns
from src.data.feature_engineering import (
    create_geolocation_zip_summary,
    create_order_item_aggregate,
    create_payment_aggregate,
    create_review_aggregate,
)
from src.data.load_data import load_raw_data, verify_raw_files
from src.data.validate_data import assert_no_row_multiplication, assert_unique_key, validate_required_schemas


def test_all_raw_files_exist():
    paths = verify_raw_files()
    assert set(paths) == set(RAW_FILES)


def test_raw_schemas_match_contract():
    tables = load_raw_data()
    validate_required_schemas(tables)
    for name, expected in EXPECTED_SCHEMAS.items():
        assert list(tables[name].columns) == expected


def test_reference_row_counts_match_supplied_files():
    tables = load_raw_data()
    assert {name: len(data) for name, data in tables.items()} == EXPECTED_ROW_COUNTS


def test_customer_id_is_unique():
    customers = pd.read_csv(verify_raw_files()["customers"])
    assert customers["customer_id"].is_unique


def test_customer_unique_id_is_durable_identity():
    customers = pd.read_csv(verify_raw_files()["customers"])
    assert customers["customer_unique_id"].nunique() == 96_096
    assert (customers["customer_unique_id"].value_counts() > 1).sum() == 2_997


def test_order_id_is_unique():
    orders = pd.read_csv(verify_raw_files()["orders"])
    assert orders["order_id"].is_unique


def test_date_conversion_preserves_valid_values():
    data = pd.DataFrame({"order_purchase_timestamp": ["2018-01-01 10:00:00", "invalid"]})
    parsed = parse_date_columns("orders", data.assign(
        order_approved_at=None,
        order_delivered_carrier_date=None,
        order_delivered_customer_date=None,
        order_estimated_delivery_date=None,
    ))
    assert parsed["order_purchase_timestamp"].notna().sum() == 1


def test_geolocation_aggregation_is_one_row_per_zip():
    data = pd.DataFrame(
        {
            "geolocation_zip_code_prefix": [1, 1, 2],
            "geolocation_lat": [-23.0, 45.0, -10.0],
            "geolocation_lng": [-46.0, 121.0, -50.0],
            "geolocation_city": ["a", "a", "b"],
            "geolocation_state": ["SP", "SP", "BA"],
        }
    )
    result = create_geolocation_zip_summary(data)
    assert len(result) == 2
    assert result["geolocation_zip_code_prefix"].is_unique
    assert result.loc[result["geolocation_zip_code_prefix"].eq(1), "geolocation_lat"].iloc[0] == -23.0


def test_order_item_aggregate_preserves_revenue():
    items = pd.DataFrame(
        {
            "order_id": ["a", "a", "b"], "order_item_id": [1, 2, 1],
            "product_id": ["p1", "p2", "p1"], "seller_id": ["s1", "s1", "s2"],
            "price": [10.0, 15.0, 20.0], "freight_value": [2.0, 3.0, 4.0],
        }
    )
    result = create_order_item_aggregate(items)
    assert result["merchandise_revenue"].sum() == items["price"].sum()
    assert result.loc[result["order_id"].eq("a"), "item_count"].iloc[0] == 2


def test_payment_aggregate_preserves_total():
    payments = pd.DataFrame(
        {
            "order_id": ["a", "a", "b"], "payment_sequential": [1, 2, 1],
            "payment_type": ["card", "voucher", "card"],
            "payment_installments": [2, 1, 1], "payment_value": [10.0, 5.0, 20.0],
        }
    )
    result = create_payment_aggregate(payments)
    assert np.isclose(result["total_payment_value"].sum(), payments["payment_value"].sum())
    assert result.loc[result["order_id"].eq("a"), "dominant_payment_type"].iloc[0] == "card"


def test_review_aggregate_handles_repeated_order_and_review_ids():
    reviews = pd.DataFrame(
        {
            "review_id": ["r", "r", "r2"], "order_id": ["a", "b", "a"],
            "review_score": [3, 4, 5],
            "review_creation_date": pd.to_datetime(["2018-01-01"] * 3),
            "review_answer_timestamp": pd.to_datetime(["2018-01-02", "2018-01-03", "2018-01-04"]),
        }
    )
    result = create_review_aggregate(reviews)
    assert result["order_id"].is_unique
    assert result.loc[result["order_id"].eq("a"), "review_score"].iloc[0] == 5


def test_clean_products_uses_translation_and_fallback():
    products = pd.DataFrame(
        {
            "product_id": ["p1", "p2", "p3"],
            "product_category_name": ["beleza", "sem_traducao", None],
            "product_weight_g": [100.0, 0.0, 50.0],
            "product_length_cm": [10.0] * 3, "product_height_cm": [10.0] * 3,
            "product_width_cm": [10.0] * 3,
        }
    )
    translation = pd.DataFrame({"product_category_name": ["beleza"], "product_category_name_english": ["health_beauty"]})
    result = clean_products(products, translation)
    assert result["product_category"].tolist() == ["Health Beauty", "Sem Traducao", "Unknown"]
    assert pd.isna(result.loc[1, "product_weight_g"])


def test_unique_key_assertion_accepts_valid_composite():
    assert_unique_key(pd.DataFrame({"a": [1, 1], "b": [1, 2]}), ["a", "b"], "sample")


def test_no_row_multiplication_assertion_accepts_safe_join():
    before = pd.DataFrame({"id": [1, 2]})
    after = before.merge(pd.DataFrame({"id": [1, 2], "x": [3, 4]}), on="id", validate="1:1")
    assert_no_row_multiplication(before, after, "sample")
