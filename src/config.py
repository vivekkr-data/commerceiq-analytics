"""Project configuration and source-data contracts."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CORE_DIR = PROCESSED_DIR / "core"
DASHBOARD_DIR = PROCESSED_DIR / "dashboard"
EXPORT_DIR = DATA_DIR / "exports"
MODEL_DIR = ROOT_DIR / "models"
REPORT_DIR = ROOT_DIR / "reports"
MODEL_RESULTS_DIR = REPORT_DIR / "model_results"

RANDOM_STATE = 42

RAW_FILES = {
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

EXPECTED_SCHEMAS = {
    "customers": [
        "customer_id", "customer_unique_id", "customer_zip_code_prefix",
        "customer_city", "customer_state",
    ],
    "orders": [
        "order_id", "customer_id", "order_status", "order_purchase_timestamp",
        "order_approved_at", "order_delivered_carrier_date",
        "order_delivered_customer_date", "order_estimated_delivery_date",
    ],
    "order_items": [
        "order_id", "order_item_id", "product_id", "seller_id",
        "shipping_limit_date", "price", "freight_value",
    ],
    "payments": [
        "order_id", "payment_sequential", "payment_type",
        "payment_installments", "payment_value",
    ],
    "reviews": [
        "review_id", "order_id", "review_score", "review_comment_title",
        "review_comment_message", "review_creation_date", "review_answer_timestamp",
    ],
    "products": [
        "product_id", "product_category_name", "product_name_lenght",
        "product_description_lenght", "product_photos_qty", "product_weight_g",
        "product_length_cm", "product_height_cm", "product_width_cm",
    ],
    "sellers": ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    "geolocation": [
        "geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
        "geolocation_city", "geolocation_state",
    ],
    "category_translation": ["product_category_name", "product_category_name_english"],
}

EXPECTED_ROW_COUNTS = {
    "customers": 99_441,
    "orders": 99_441,
    "order_items": 112_650,
    "payments": 103_886,
    "reviews": 99_224,
    "products": 32_951,
    "sellers": 3_095,
    "geolocation": 1_000_163,
    "category_translation": 71,
}

DATE_COLUMNS = {
    "orders": [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items": ["shipping_limit_date"],
    "reviews": ["review_creation_date", "review_answer_timestamp"],
}

DELIVERY_MODEL_FEATURES = [
    "purchase_month", "purchase_weekday", "purchase_hour", "customer_state",
    "seller_state", "product_category", "item_count", "unique_product_count",
    "unique_seller_count", "merchandise_revenue", "total_freight_value",
    "gross_order_value", "total_payment_value", "maximum_installments",
    "dominant_payment_type", "distance_km", "estimated_delivery_days",
    "average_product_weight_g",
]

POST_OUTCOME_COLUMNS = {
    "late_delivery", "order_delivered_customer_date", "order_delivered_carrier_date",
    "delivery_days", "delivery_delay_days", "review_score", "average_review_score",
}
