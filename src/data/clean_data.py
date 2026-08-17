"""Context-aware cleaning that preserves source lineage."""

from __future__ import annotations

import pandas as pd

from src.config import DATE_COLUMNS


def clean_text_columns(data: pd.DataFrame) -> pd.DataFrame:
    cleaned = data.copy()
    for column in cleaned.select_dtypes(include=["object", "string"]).columns:
        cleaned[column] = cleaned[column].str.strip()
    return cleaned


def parse_date_columns(name: str, data: pd.DataFrame) -> pd.DataFrame:
    cleaned = data.copy()
    for column in DATE_COLUMNS.get(name, []):
        cleaned[column] = pd.to_datetime(cleaned[column], errors="coerce")
    return cleaned


def clean_products(products: pd.DataFrame, translation: pd.DataFrame) -> pd.DataFrame:
    cleaned = clean_text_columns(products)
    translated = cleaned.merge(
        translation, on="product_category_name", how="left", validate="m:1"
    )
    translated["product_category"] = translated["product_category_name_english"].fillna(
        translated["product_category_name"]
    ).fillna("Unknown")
    translated["product_category"] = translated["product_category"].str.replace("_", " ").str.title()
    for column in ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]:
        translated.loc[translated[column] <= 0, column] = pd.NA
    return translated


def clean_tables(raw_tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    cleaned: dict[str, pd.DataFrame] = {}
    for name, data in raw_tables.items():
        cleaned[name] = parse_date_columns(name, clean_text_columns(data))
    cleaned["products"] = clean_products(cleaned["products"], cleaned["category_translation"])
    return cleaned
