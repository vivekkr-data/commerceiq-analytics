"""CommerceIQ Analytics Streamlit entry point."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


APP_DIR = Path(__file__).resolve().parent
# Streamlit can execute ``app/app.py`` with the module name ``app``.  In that
# mode Python treats this file as a plain module, which would otherwise shadow
# the real ``app`` package and break imports such as ``app.components``.
if __name__ == "app" and "__path__" not in globals():
    __path__ = [str(APP_DIR)]

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) in sys.path:
    sys.path.remove(str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR))

from app.components.helpers import inject_app_styles  # noqa: E402
from app.pages import (  # noqa: E402
    customer_analytics,
    delivery_risk,
    delivery_satisfaction,
    forecasting,
    model_performance,
    overview,
    product_analytics,
    retention_analysis,
    sales_analytics,
    segmentation,
)


def main() -> None:
    st.set_page_config(
        page_title="CommerceIQ Analytics",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_app_styles()
    navigation = st.navigation(
        {
            "Business Analytics": [
                st.Page(overview.render, title="Executive Overview", icon=":material/dashboard:", url_path="overview", default=True),
                st.Page(sales_analytics.render, title="Sales Analytics", icon=":material/trending_up:", url_path="sales"),
                st.Page(customer_analytics.render, title="Customer Analytics", icon=":material/groups:", url_path="customers"),
                st.Page(product_analytics.render, title="Product Analytics", icon=":material/inventory_2:", url_path="products"),
                st.Page(delivery_satisfaction.render, title="Delivery & Satisfaction", icon=":material/local_shipping:", url_path="delivery-satisfaction"),
            ],
            "Data Science": [
                st.Page(segmentation.render, title="Customer Segmentation", icon=":material/hub:", url_path="segmentation"),
                st.Page(delivery_risk.render, title="Delivery Risk", icon=":material/warning:", url_path="delivery-risk"),
                st.Page(retention_analysis.render, title="Retention Analysis", icon=":material/refresh:", url_path="retention"),
                st.Page(forecasting.render, title="Sales Forecast", icon=":material/query_stats:", url_path="forecast"),
                st.Page(model_performance.render, title="Model Performance", icon=":material/analytics:", url_path="models"),
            ],
        }
    )
    navigation.run()


if __name__ == "__main__":
    main()
