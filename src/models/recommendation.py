"""Category co-purchase and popularity recommendations."""

from __future__ import annotations

import pandas as pd


def build_category_recommendations(
    enriched_items: pd.DataFrame, order_level: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    delivered_orders = set(
        order_level.loc[order_level["order_status"].eq("delivered"), "order_id"]
    )
    categories = enriched_items.loc[
        enriched_items["order_id"].isin(delivered_orders),
        ["order_id", "product_category"],
    ].drop_duplicates()
    category_orders = categories.groupby("product_category")["order_id"].nunique()
    pairs = categories.merge(categories, on="order_id", suffixes=("_source", "_target"))
    pairs = pairs[pairs["product_category_source"] < pairs["product_category_target"]]
    pair_counts = (
        pairs.groupby(["product_category_source", "product_category_target"])
        .size().rename("co_purchase_orders").reset_index()
    )
    reverse = pair_counts.rename(
        columns={
            "product_category_source": "product_category_target",
            "product_category_target": "product_category_source",
        }
    )
    directed = pd.concat([pair_counts, reverse], ignore_index=True)
    directed["source_orders"] = directed["product_category_source"].map(category_orders)
    directed["recommendation_strength"] = directed["co_purchase_orders"] / directed["source_orders"]
    recommendations = (
        directed.sort_values(
            ["product_category_source", "co_purchase_orders", "recommendation_strength"],
            ascending=[True, False, False],
        )
        .groupby("product_category_source", as_index=False)
        .head(5)
        .rename(
            columns={
                "product_category_source": "source_category",
                "product_category_target": "recommended_category",
            }
        )
    )
    popularity = (
        category_orders.sort_values(ascending=False).head(10)
        .rename("orders").rename_axis("product_category").reset_index()
    )
    return recommendations, popularity
