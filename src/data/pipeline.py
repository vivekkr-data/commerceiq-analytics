"""End-to-end data, analytics, modelling, and artifact pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from src.analytics.customers import build_customer_state_summary
from src.analytics.delivery import build_delivery_state_summary
from src.analytics.insights import generate_business_insights
from src.analytics.kpis import calculate_kpis
from src.analytics.reviews import build_delay_review_summary, build_review_distribution
from src.analytics.sales import build_payment_summary, build_state_sales
from src.config import (
    CORE_DIR, DASHBOARD_DIR, MODEL_DIR, MODEL_RESULTS_DIR, POST_OUTCOME_COLUMNS,
    ROOT_DIR,
)
from src.data.clean_data import clean_tables
from src.data.feature_engineering import (
    add_customer_geolocation,
    add_seller_geolocation,
    build_cohort_retention,
    build_customer_features,
    build_order_level,
    build_product_summary,
    build_seller_summary,
    calculate_monthly_sales,
    create_geolocation_zip_summary,
    create_order_context,
    create_order_item_aggregate,
    create_payment_aggregate,
    create_review_aggregate,
    enrich_order_items,
)
from src.data.load_data import load_raw_data
from src.data.validate_data import assert_columns_excluded, build_validation_report
from src.database.connection import create_database_engine, database_configured
from src.database.load_database import create_schema, load_postgresql
from src.models.customer_value import build_historical_customer_value
from src.models.delivery_risk import train_delivery_model
from src.models.forecasting import train_forecast_models
from src.models.recommendation import build_category_recommendations
from src.models.retention import evaluate_retention_feasibility
from src.models.segmentation import train_segmentation
from src.utils.logger import get_logger
from src.utils.paths import ensure_output_directories


LOGGER = get_logger()


def _json_default(value: object) -> object:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, (pd.Timestamp, Path)):
        return str(value)
    if pd.isna(value):
        return None
    raise TypeError(f"Cannot serialize {type(value)}")


def save_json(value: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )


def _save_parquet(data: pd.DataFrame, name: str, directory: Path = DASHBOARD_DIR) -> None:
    data.to_parquet(directory / f"{name}.parquet", index=False)


def _build_model_metrics(
    delivery: pd.DataFrame,
    forecast: pd.DataFrame,
    segmentation: pd.DataFrame,
    retention: pd.DataFrame,
) -> pd.DataFrame:
    frames = []
    for module, data in [
        ("Delivery Risk", delivery),
        ("Forecasting", forecast),
        ("Segmentation", segmentation),
        ("Retention", retention),
    ]:
        item = data.copy()
        item.insert(0, "module", module)
        frames.append(item)
    return pd.concat(frames, ignore_index=True, sort=False)


def _validate_analytical_grains(
    raw: dict[str, pd.DataFrame],
    order_level: pd.DataFrame,
    customer_features: pd.DataFrame,
    geolocation_summary: pd.DataFrame,
    item_aggregate: pd.DataFrame,
    payment_aggregate: pd.DataFrame,
) -> None:
    if len(order_level) != len(raw["orders"]) or order_level["order_id"].nunique() != len(order_level):
        raise AssertionError("Order-level table is not one row per order_id")
    expected_customers = raw["customers"]["customer_unique_id"].nunique()
    if len(customer_features) != expected_customers:
        raise AssertionError("Customer table is not one row per customer_unique_id")
    if geolocation_summary["geolocation_zip_code_prefix"].duplicated().any():
        raise AssertionError("Geolocation ZIP summary is not unique")
    if item_aggregate["order_id"].duplicated().any() or payment_aggregate["order_id"].duplicated().any():
        raise AssertionError("Order aggregates are not unique")
    if not np.isclose(item_aggregate["merchandise_revenue"].sum(), raw["order_items"]["price"].sum()):
        raise AssertionError("Item aggregation inflated merchandise revenue")
    if not np.isclose(payment_aggregate["total_payment_value"].sum(), raw["payments"]["payment_value"].sum()):
        raise AssertionError("Payment aggregation inflated payment totals")


def run_pipeline() -> dict[str, object]:
    load_dotenv(ROOT_DIR / ".env")
    ensure_output_directories()
    LOGGER.info("Loading and validating nine raw Olist files")
    raw = load_raw_data()
    validation_report = build_validation_report(raw)
    save_json(validation_report, MODEL_RESULTS_DIR / "data_validation.json")

    LOGGER.info("Cleaning data and creating duplicate-safe order aggregates")
    cleaned = clean_tables(raw)
    geolocation_summary = create_geolocation_zip_summary(cleaned["geolocation"])
    customers_geo = add_customer_geolocation(cleaned["customers"], geolocation_summary)
    sellers_geo = add_seller_geolocation(cleaned["sellers"], geolocation_summary)
    enriched_items = enrich_order_items(cleaned["order_items"], cleaned["products"], sellers_geo)
    item_aggregate = create_order_item_aggregate(cleaned["order_items"])
    payment_aggregate = create_payment_aggregate(cleaned["payments"])
    review_aggregate = create_review_aggregate(cleaned["reviews"])
    order_context = create_order_context(enriched_items)
    order_level = build_order_level(
        cleaned["orders"], customers_geo, item_aggregate,
        payment_aggregate, review_aggregate, order_context,
    )
    customer_features = build_customer_features(order_level, enriched_items)
    _validate_analytical_grains(
        raw, order_level, customer_features, geolocation_summary,
        item_aggregate, payment_aggregate,
    )

    LOGGER.info("Creating analytical and dashboard-ready datasets")
    monthly_sales = calculate_monthly_sales(order_level)
    product_summary = build_product_summary(enriched_items, order_level)
    seller_summary = build_seller_summary(enriched_items, order_level)
    cohort_retention = build_cohort_retention(order_level)
    state_sales = build_state_sales(order_level)
    payment_summary = build_payment_summary(order_level)
    customer_state = build_customer_state_summary(customer_features)
    delivery_state = build_delivery_state_summary(order_level)
    review_distribution = build_review_distribution(order_level)
    delay_review = build_delay_review_summary(order_level)
    customer_value = build_historical_customer_value(customer_features)
    recommendations, popularity = build_category_recommendations(enriched_items, order_level)

    LOGGER.info("Training RFM segmentation")
    customer_segments, segment_summary, segmentation_metrics, segmentation_meta = train_segmentation(
        customer_features, MODEL_DIR / "segmentation.joblib"
    )
    LOGGER.info("Training and evaluating late-delivery classifiers")
    delivery_metrics, delivery_predictions, delivery_importance, delivery_outputs = train_delivery_model(
        order_level, MODEL_DIR / "delivery_risk.joblib"
    )
    LOGGER.info("Evaluating temporal retention modelling feasibility")
    retention_metrics, retention_predictions, retention_meta = evaluate_retention_feasibility(
        order_level, MODEL_DIR / "retention.joblib"
    )
    LOGGER.info("Training chronological sales forecasts")
    forecast_metrics, forecast_history, forecast_meta = train_forecast_models(
        monthly_sales, MODEL_DIR / "sales_forecast.joblib"
    )
    monthly_sales["is_complete"] = monthly_sales["purchase_period"].le(
        pd.Timestamp(forecast_meta["complete_cutoff"])
    )

    model_metrics = _build_model_metrics(
        delivery_metrics, forecast_metrics, segmentation_metrics, retention_metrics
    )
    kpis = calculate_kpis(order_level, customer_features)
    insights = generate_business_insights(
        order_level, customer_features, monthly_sales, product_summary,
        seller_summary, state_sales, payment_summary, delay_review,
    )

    assert_columns_excluded(delivery_outputs["metadata"].get("features", []), POST_OUTCOME_COLUMNS)
    LOGGER.info("Saving processed core and dashboard artifacts")
    core_outputs = {
        "geolocation_zip_summary": geolocation_summary,
        "order_items_order_level": item_aggregate,
        "payments_order_level": payment_aggregate,
        "reviews_order_level": review_aggregate,
        "order_level": order_level,
        "customer_level": customer_features,
        "seller_order_items": enriched_items,
    }
    for name, data in core_outputs.items():
        _save_parquet(data, name, CORE_DIR)

    dashboard_outputs = {
        "overview": order_level,
        "monthly_sales": monthly_sales,
        "customer_features": customer_value,
        "customer_segments": customer_segments,
        "segment_summary": segment_summary,
        "delivery_analysis": order_level[
            [
                "order_id", "order_purchase_timestamp", "customer_state", "seller_state",
                "delivery_days", "delivery_delay_days", "late_delivery", "total_freight_value",
                "average_review_score", "review_score", "distance_km",
            ]
        ],
        "delivery_predictions": delivery_predictions,
        "delivery_feature_importance": delivery_importance,
        "delivery_confusion_matrix": delivery_outputs["confusion"],
        "delivery_roc_curve": delivery_outputs["roc_curve"],
        "delivery_pr_curve": delivery_outputs["pr_curve"],
        "retention_predictions": retention_predictions,
        "cohort_retention": cohort_retention,
        "forecast_history": forecast_history,
        "product_summary": product_summary,
        "seller_summary": seller_summary,
        "state_sales": state_sales,
        "customer_state_summary": customer_state,
        "delivery_state_summary": delivery_state,
        "payment_summary": payment_summary,
        "review_distribution": review_distribution,
        "delay_review_summary": delay_review,
        "category_recommendations": recommendations,
        "category_popularity": popularity,
    }
    for name, data in dashboard_outputs.items():
        _save_parquet(data, name)
    model_metrics.to_csv(DASHBOARD_DIR / "model_metrics.csv", index=False)
    pd.DataFrame(insights).to_csv(DASHBOARD_DIR / "business_insights.csv", index=False)
    pd.DataFrame([kpis]).to_csv(DASHBOARD_DIR / "kpis.csv", index=False)

    results = {
        "validation": validation_report,
        "kpis": kpis,
        "segmentation": segmentation_meta,
        "delivery_risk": delivery_outputs["metadata"],
        "retention": retention_meta,
        "forecast": forecast_meta,
        "insights": insights,
    }
    save_json(results, MODEL_RESULTS_DIR / "pipeline_results.json")

    database_status = "not requested"
    if os.getenv("LOAD_POSTGRES", "false").lower() == "true":
        if not database_configured():
            database_status = "skipped: credentials incomplete"
            LOGGER.warning("PostgreSQL load requested but credentials are incomplete")
        else:
            LOGGER.info("Loading optional PostgreSQL layer")
            engine = create_database_engine()
            create_schema(engine, ROOT_DIR / "sql" / "schema.sql")
            load_postgresql(engine, cleaned)
            database_status = "loaded"
    results["database_status"] = database_status
    save_json(results, MODEL_RESULTS_DIR / "pipeline_results.json")
    LOGGER.info("Pipeline completed successfully")
    return results
