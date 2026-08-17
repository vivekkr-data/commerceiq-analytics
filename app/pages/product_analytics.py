"""Product and category analytics page."""

import plotly.express as px
import streamlit as st

from app.components.cards import metric_row
from app.components.charts import PRIMARY, style_figure
from app.components.helpers import format_brl, load_parquet, page_header


def render() -> None:
    page_header("Product Analytics", "Category performance and understandable co-purchase recommendations")
    products = load_parquet("product_summary")
    top = products.iloc[0]
    metric_row(
        [
            ("Leading Category", str(top["product_category"]), None),
            ("Category Revenue", format_brl(top["merchandise_revenue"], compact=True), None),
            ("Units Sold", f"{int(products['units_sold'].sum()):,}", None),
            ("Average Category Review", f"{products['average_review'].mean():.2f}/5", None),
            ("Categories", f"{len(products):,}", None),
        ]
    )
    left, right = st.columns(2)
    with left:
        chart = products.head(15).sort_values("merchandise_revenue")
        figure = px.bar(chart, x="merchandise_revenue", y="product_category", orientation="h", title="Top Categories by Revenue")
        figure.update_traces(marker_color=PRIMARY)
        st.plotly_chart(style_figure(figure, 520), width="stretch")
    with right:
        figure = px.scatter(
            products,
            x="average_price", y="merchandise_revenue", size="units_sold",
            color="average_review", hover_name="product_category",
            title="Category Price, Revenue, and Review Profile", color_continuous_scale="Blues",
        )
        st.plotly_chart(style_figure(figure, 520), width="stretch")
    display = products[[
        "product_category", "merchandise_revenue", "units_sold", "order_count",
        "average_price", "average_freight", "average_review", "category_share",
    ]]
    st.dataframe(display, width="stretch", hide_index=True)
    st.subheader("Category Co-Purchase Recommendations")
    recommendations = load_parquet("category_recommendations")
    popularity = load_parquet("category_popularity")
    if recommendations.empty:
        st.info("Cross-category pairs are sparse; use the popularity fallback below.")
        st.dataframe(popularity, width="stretch", hide_index=True)
    else:
        source = st.selectbox("Customer viewed or purchased", sorted(recommendations["source_category"].unique()))
        selected = recommendations[recommendations["source_category"].eq(source)][
            ["recommended_category", "co_purchase_orders", "recommendation_strength"]
        ]
        st.dataframe(selected, width="stretch", hide_index=True)
        st.caption("Recommendations describe observed category co-purchases. No recommendation accuracy is claimed.")
