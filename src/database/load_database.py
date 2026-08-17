"""Optional PostgreSQL schema creation and data loading."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.config import EXPECTED_SCHEMAS


TABLE_MAP = {
    "customers": "customers",
    "orders": "orders",
    "order_items": "order_items",
    "payments": "order_payments",
    "reviews": "order_reviews",
    "products": "products",
    "sellers": "sellers",
    "geolocation": "geolocation",
    "category_translation": "product_category_translation",
}


def create_schema(engine: Engine, schema_path: Path) -> None:
    sql = schema_path.read_text(encoding="utf-8")
    with engine.begin() as connection:
        connection.execute(text(sql))


def load_postgresql(engine: Engine, tables: dict[str, pd.DataFrame]) -> None:
    with engine.begin() as connection:
        for source_name, table_name in TABLE_MAP.items():
            connection.execute(text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'))
            tables[source_name][EXPECTED_SCHEMAS[source_name]].to_sql(
                table_name,
                connection,
                if_exists="append",
                index=False,
                chunksize=10_000,
                method="multi",
            )
