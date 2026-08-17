"""Grain-safe analytical tables and engineered features."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.validate_data import assert_no_row_multiplication, assert_unique_key


def _representative_location(geolocation: pd.DataFrame) -> pd.DataFrame:
    counts = (
        geolocation.groupby(
            ["geolocation_zip_code_prefix", "geolocation_state", "geolocation_city"],
            dropna=False,
        )
        .size()
        .rename("location_count")
        .reset_index()
        .sort_values(
            ["geolocation_zip_code_prefix", "location_count", "geolocation_state", "geolocation_city"],
            ascending=[True, False, True, True],
        )
        .drop_duplicates("geolocation_zip_code_prefix")
    )
    return counts.drop(columns="location_count")


def create_geolocation_zip_summary(geolocation: pd.DataFrame) -> pd.DataFrame:
    """Return one representative row per ZIP prefix using robust median coordinates."""
    valid = geolocation.copy()
    brazil_bounds = (
        valid["geolocation_lat"].between(-34.0, 6.0)
        & valid["geolocation_lng"].between(-75.0, -30.0)
    )
    valid.loc[~brazil_bounds, ["geolocation_lat", "geolocation_lng"]] = np.nan
    coordinates = (
        valid.groupby("geolocation_zip_code_prefix", as_index=False)
        .agg(
            geolocation_lat=("geolocation_lat", "median"),
            geolocation_lng=("geolocation_lng", "median"),
            geolocation_source_rows=("geolocation_state", "size"),
        )
    )
    representative = _representative_location(geolocation)
    summary = coordinates.merge(
        representative, on="geolocation_zip_code_prefix", how="left", validate="1:1"
    )
    assert_unique_key(summary, ["geolocation_zip_code_prefix"], "geolocation_zip_summary")
    return summary


def add_customer_geolocation(
    customers: pd.DataFrame, geolocation_summary: pd.DataFrame
) -> pd.DataFrame:
    renamed = geolocation_summary.rename(
        columns={
            "geolocation_zip_code_prefix": "customer_zip_code_prefix",
            "geolocation_lat": "customer_lat",
            "geolocation_lng": "customer_lng",
            "geolocation_city": "zip_city",
            "geolocation_state": "zip_state",
        }
    )
    result = customers.merge(
        renamed[
            ["customer_zip_code_prefix", "customer_lat", "customer_lng", "zip_city", "zip_state"]
        ],
        on="customer_zip_code_prefix",
        how="left",
        validate="m:1",
    )
    assert_no_row_multiplication(customers, result, "customer")
    return result


def add_seller_geolocation(
    sellers: pd.DataFrame, geolocation_summary: pd.DataFrame
) -> pd.DataFrame:
    renamed = geolocation_summary.rename(
        columns={
            "geolocation_zip_code_prefix": "seller_zip_code_prefix",
            "geolocation_lat": "seller_lat",
            "geolocation_lng": "seller_lng",
            "geolocation_city": "seller_zip_city",
            "geolocation_state": "seller_zip_state",
        }
    )
    result = sellers.merge(
        renamed[
            [
                "seller_zip_code_prefix", "seller_lat", "seller_lng",
                "seller_zip_city", "seller_zip_state",
            ]
        ],
        on="seller_zip_code_prefix",
        how="left",
        validate="m:1",
    )
    assert_no_row_multiplication(sellers, result, "seller")
    return result


def create_order_item_aggregate(order_items: pd.DataFrame) -> pd.DataFrame:
    aggregate = (
        order_items.groupby("order_id", as_index=False)
        .agg(
            item_count=("order_item_id", "size"),
            unique_product_count=("product_id", "nunique"),
            unique_seller_count=("seller_id", "nunique"),
            merchandise_revenue=("price", "sum"),
            total_freight_value=("freight_value", "sum"),
        )
    )
    assert_unique_key(aggregate, ["order_id"], "order_items_order_level")
    return aggregate


def create_payment_aggregate(payments: pd.DataFrame) -> pd.DataFrame:
    type_value = (
        payments.groupby(["order_id", "payment_type"], as_index=False)["payment_value"]
        .sum()
        .sort_values(["order_id", "payment_value", "payment_type"], ascending=[True, False, True])
        .drop_duplicates("order_id")
        .rename(columns={"payment_type": "dominant_payment_type"})
        [["order_id", "dominant_payment_type"]]
    )
    aggregate = (
        payments.groupby("order_id", as_index=False)
        .agg(
            total_payment_value=("payment_value", "sum"),
            payment_record_count=("payment_sequential", "size"),
            payment_type_count=("payment_type", "nunique"),
            maximum_installments=("payment_installments", "max"),
        )
        .merge(type_value, on="order_id", how="left", validate="1:1")
    )
    assert_unique_key(aggregate, ["order_id"], "payments_order_level")
    return aggregate


def create_review_aggregate(reviews: pd.DataFrame) -> pd.DataFrame:
    summary = (
        reviews.groupby("order_id", as_index=False)
        .agg(
            average_review_score=("review_score", "mean"),
            review_count=("review_id", "size"),
        )
    )
    latest = (
        reviews.sort_values(["order_id", "review_answer_timestamp", "review_id"])
        .drop_duplicates("order_id", keep="last")
        [["order_id", "review_id", "review_score", "review_creation_date", "review_answer_timestamp"]]
    )
    aggregate = summary.merge(latest, on="order_id", how="left", validate="1:1")
    assert_unique_key(aggregate, ["order_id"], "reviews_order_level")
    return aggregate


def enrich_order_items(
    order_items: pd.DataFrame,
    products: pd.DataFrame,
    sellers_geo: pd.DataFrame,
) -> pd.DataFrame:
    product_columns = ["product_id", "product_category", "product_weight_g"]
    seller_columns = ["seller_id", "seller_state", "seller_lat", "seller_lng"]
    enriched = order_items.merge(
        products[product_columns], on="product_id", how="left", validate="m:1"
    ).merge(sellers_geo[seller_columns], on="seller_id", how="left", validate="m:1")
    assert_no_row_multiplication(order_items, enriched, "order-item")
    enriched["product_category"] = enriched["product_category"].fillna("Unknown")
    return enriched


def create_order_context(enriched_items: pd.DataFrame) -> pd.DataFrame:
    primary = (
        enriched_items.assign(line_value=enriched_items["price"] + enriched_items["freight_value"])
        .sort_values(
            ["order_id", "line_value", "order_item_id"],
            ascending=[True, False, True],
        )
        .drop_duplicates("order_id")
        [["order_id", "product_category", "seller_state", "seller_lat", "seller_lng"]]
    )
    weights = (
        enriched_items.groupby("order_id", as_index=False)
        .agg(average_product_weight_g=("product_weight_g", "mean"))
    )
    context = primary.merge(weights, on="order_id", how="left", validate="1:1")
    assert_unique_key(context, ["order_id"], "order_context")
    return context


def haversine_distance_km(
    lat1: pd.Series, lng1: pd.Series, lat2: pd.Series, lng2: pd.Series
) -> pd.Series:
    radius_km = 6371.0088
    lat1_rad = np.radians(lat1.astype(float))
    lat2_rad = np.radians(lat2.astype(float))
    delta_lat = lat2_rad - lat1_rad
    delta_lng = np.radians(lng2.astype(float) - lng1.astype(float))
    a = np.sin(delta_lat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lng / 2) ** 2
    return pd.Series(radius_km * 2 * np.arcsin(np.sqrt(a)), index=lat1.index)


def build_order_level(
    orders: pd.DataFrame,
    customers_geo: pd.DataFrame,
    item_aggregate: pd.DataFrame,
    payment_aggregate: pd.DataFrame,
    review_aggregate: pd.DataFrame,
    order_context: pd.DataFrame,
) -> pd.DataFrame:
    """Build one safe row per order after aggregating every one-to-many source."""
    order_level = orders.merge(customers_geo, on="customer_id", how="left", validate="m:1")
    assert_no_row_multiplication(orders, order_level, "order")
    for table in [item_aggregate, payment_aggregate, review_aggregate, order_context]:
        before = order_level
        order_level = order_level.merge(table, on="order_id", how="left", validate="1:1")
        assert_no_row_multiplication(before, order_level, "order")

    count_columns = [
        "item_count", "unique_product_count", "unique_seller_count",
        "payment_record_count", "payment_type_count", "review_count",
    ]
    for column in count_columns:
        order_level[column] = order_level[column].fillna(0).astype(int)
    for column in [
        "merchandise_revenue", "total_freight_value", "total_payment_value",
    ]:
        order_level[column] = order_level[column].fillna(0.0)

    order_level["gross_order_value"] = (
        order_level["merchandise_revenue"] + order_level["total_freight_value"]
    )
    purchase = order_level["order_purchase_timestamp"]
    order_level["purchase_year"] = purchase.dt.year.astype("Int64")
    order_level["purchase_month"] = purchase.dt.month.astype("Int64")
    order_level["purchase_weekday"] = purchase.dt.dayofweek.astype("Int64")
    order_level["purchase_hour"] = purchase.dt.hour.astype("Int64")
    order_level["purchase_period"] = purchase.dt.to_period("M").dt.to_timestamp()
    order_level["delivery_days"] = (
        order_level["order_delivered_customer_date"] - purchase
    ).dt.total_seconds() / 86_400
    order_level["delivery_delay_days"] = (
        order_level["order_delivered_customer_date"]
        - order_level["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86_400
    order_level["estimated_delivery_days"] = (
        order_level["order_estimated_delivery_date"] - purchase
    ).dt.total_seconds() / 86_400
    delivered_with_dates = (
        order_level["order_status"].eq("delivered")
        & order_level["order_delivered_customer_date"].notna()
        & order_level["order_estimated_delivery_date"].notna()
    )
    order_level["late_delivery"] = pd.Series(pd.NA, index=order_level.index, dtype="Int64")
    order_level.loc[delivered_with_dates, "late_delivery"] = (
        order_level.loc[delivered_with_dates, "delivery_delay_days"] > 0
    ).astype(int)
    order_level["realized_merchandise_revenue"] = np.where(
        order_level["order_status"].eq("delivered"),
        order_level["merchandise_revenue"],
        0.0,
    )
    order_level["realized_freight_value"] = np.where(
        order_level["order_status"].eq("delivered"),
        order_level["total_freight_value"],
        0.0,
    )
    order_level["distance_km"] = haversine_distance_km(
        order_level["customer_lat"], order_level["customer_lng"],
        order_level["seller_lat"], order_level["seller_lng"],
    )
    order_level["product_category"] = order_level["product_category"].fillna("Unknown")
    order_level["seller_state"] = order_level["seller_state"].fillna("Unknown")
    order_level["dominant_payment_type"] = order_level["dominant_payment_type"].fillna("not_available")
    assert_unique_key(order_level, ["order_id"], "order_level")
    return order_level


def build_customer_features(
    order_level: pd.DataFrame, enriched_items: pd.DataFrame
) -> pd.DataFrame:
    reference_date = order_level["order_purchase_timestamp"].max().normalize() + pd.Timedelta(days=1)
    base = order_level.copy()
    base["is_delivered"] = base["order_status"].eq("delivered").astype(int)
    base["delivered_items"] = np.where(base["is_delivered"].eq(1), base["item_count"], 0)
    grouped = (
        base.groupby("customer_unique_id", as_index=False)
        .agg(
            total_orders=("order_id", "nunique"),
            delivered_orders=("is_delivered", "sum"),
            total_spend=("realized_merchandise_revenue", "sum"),
            total_items=("delivered_items", "sum"),
            first_purchase_date=("order_purchase_timestamp", "min"),
            last_purchase_date=("order_purchase_timestamp", "max"),
            average_review_score=("average_review_score", "mean"),
            average_delivery_days=("delivery_days", "mean"),
            late_delivery_rate=("late_delivery", "mean"),
            average_freight=("realized_freight_value", "mean"),
            customer_state=("customer_state", "first"),
            customer_city=("customer_city", "first"),
        )
    )
    grouped["average_order_value"] = grouped["total_spend"].div(
        grouped["delivered_orders"].replace(0, np.nan)
    )
    grouped["recency"] = (reference_date - grouped["last_purchase_date"]).dt.days
    grouped["frequency"] = grouped["delivered_orders"]
    grouped["monetary"] = grouped["total_spend"]
    grouped["customer_tenure"] = (
        grouped["last_purchase_date"] - grouped["first_purchase_date"]
    ).dt.days
    grouped["repeat_customer"] = grouped["total_orders"].gt(1)

    item_customers = enriched_items.merge(
        order_level[["order_id", "customer_unique_id", "order_status"]],
        on="order_id", how="inner", validate="m:1",
    )
    item_customers = item_customers[item_customers["order_status"].eq("delivered")]
    diversity = (
        item_customers.groupby("customer_unique_id", as_index=False)
        .agg(
            product_diversity=("product_id", "nunique"),
            category_diversity=("product_category", "nunique"),
        )
    )
    features = grouped.merge(diversity, on="customer_unique_id", how="left", validate="1:1")
    features[["product_diversity", "category_diversity"]] = features[
        ["product_diversity", "category_diversity"]
    ].fillna(0).astype(int)
    assert_unique_key(features, ["customer_unique_id"], "customer_features")
    return features


def calculate_monthly_sales(order_level: pd.DataFrame) -> pd.DataFrame:
    delivered = order_level[order_level["order_status"].eq("delivered")].copy()
    delivered_monthly = (
        delivered.groupby("purchase_period", as_index=False)
        .agg(
            merchandise_revenue=("merchandise_revenue", "sum"),
            freight_value=("total_freight_value", "sum"),
            orders=("order_id", "nunique"),
            customers=("customer_unique_id", "nunique"),
            items_sold=("item_count", "sum"),
        )
    )
    all_order_counts = (
        order_level.groupby("purchase_period", as_index=False)
        .agg(all_orders=("order_id", "nunique"))
    )
    monthly = all_order_counts.merge(
        delivered_monthly, on="purchase_period", how="left", validate="1:1"
    ).sort_values("purchase_period")
    value_columns = [
        "merchandise_revenue", "freight_value", "orders", "customers", "items_sold"
    ]
    monthly[value_columns] = monthly[value_columns].fillna(0)
    monthly[["all_orders", "orders", "customers", "items_sold"]] = monthly[
        ["all_orders", "orders", "customers", "items_sold"]
    ].astype(int)
    monthly["gross_order_value"] = monthly["merchandise_revenue"] + monthly["freight_value"]
    monthly["average_order_value"] = monthly["merchandise_revenue"].div(
        monthly["orders"].replace(0, np.nan)
    )
    monthly["revenue_growth"] = monthly["merchandise_revenue"].pct_change()
    return monthly


def build_product_summary(
    enriched_items: pd.DataFrame, order_level: pd.DataFrame
) -> pd.DataFrame:
    order_columns = ["order_id", "order_status", "average_review_score"]
    delivered_items = enriched_items.merge(
        order_level[order_columns], on="order_id", how="inner", validate="m:1"
    )
    delivered_items = delivered_items[delivered_items["order_status"].eq("delivered")]
    category_order = (
        delivered_items.groupby(["product_category", "order_id"], as_index=False)
        .agg(
            units=("order_item_id", "size"),
            merchandise_revenue=("price", "sum"),
            freight_value=("freight_value", "sum"),
            average_price=("price", "mean"),
            average_freight=("freight_value", "mean"),
            average_review=("average_review_score", "first"),
        )
    )
    summary = (
        category_order.groupby("product_category", as_index=False)
        .agg(
            order_count=("order_id", "nunique"),
            units_sold=("units", "sum"),
            merchandise_revenue=("merchandise_revenue", "sum"),
            average_price=("average_price", "mean"),
            average_freight=("average_freight", "mean"),
            average_review=("average_review", "mean"),
        )
        .sort_values("merchandise_revenue", ascending=False)
    )
    summary["category_share"] = summary["merchandise_revenue"] / summary["merchandise_revenue"].sum()
    return summary


def build_seller_summary(
    enriched_items: pd.DataFrame, order_level: pd.DataFrame
) -> pd.DataFrame:
    seller_order = (
        enriched_items.groupby(["seller_id", "order_id", "seller_state"], as_index=False)
        .agg(
            units_sold=("order_item_id", "size"),
            merchandise_revenue=("price", "sum"),
            category_reach=("product_category", "nunique"),
        )
        .merge(
            order_level[
                ["order_id", "order_status", "average_review_score", "delivery_days", "late_delivery", "customer_state"]
            ],
            on="order_id", how="left", validate="m:1",
        )
    )
    seller_order = seller_order[seller_order["order_status"].eq("delivered")]
    summary = (
        seller_order.groupby(["seller_id", "seller_state"], as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            merchandise_revenue=("merchandise_revenue", "sum"),
            units_sold=("units_sold", "sum"),
            average_review_score=("average_review_score", "mean"),
            average_delivery_days=("delivery_days", "mean"),
            late_delivery_rate=("late_delivery", "mean"),
            category_reach=("category_reach", "sum"),
            geographic_reach=("customer_state", "nunique"),
        )
        .sort_values("merchandise_revenue", ascending=False)
    )
    return summary


def build_cohort_retention(order_level: pd.DataFrame) -> pd.DataFrame:
    delivered = order_level[order_level["order_status"].eq("delivered")].copy()
    delivered["order_month"] = delivered["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    delivered["cohort_month"] = delivered.groupby("customer_unique_id")["order_month"].transform("min")
    delivered["cohort_index"] = (
        (delivered["order_month"].dt.year - delivered["cohort_month"].dt.year) * 12
        + delivered["order_month"].dt.month
        - delivered["cohort_month"].dt.month
    )
    counts = (
        delivered.groupby(["cohort_month", "cohort_index"])["customer_unique_id"]
        .nunique()
        .rename("customers")
        .reset_index()
    )
    cohort_sizes = counts[counts["cohort_index"].eq(0)][["cohort_month", "customers"]].rename(
        columns={"customers": "cohort_size"}
    )
    retention = counts.merge(cohort_sizes, on="cohort_month", how="left", validate="m:1")
    retention["retention_rate"] = retention["customers"] / retention["cohort_size"]
    return retention
