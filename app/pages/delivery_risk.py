"""Late-delivery risk model page."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.components.cards import metric_row
from app.components.charts import RISK, style_figure
from app.components.helpers import download_csv, format_brl, format_percent, load_csv, load_model, load_parquet, load_results, page_header


def _selected_delivery_metrics() -> pd.Series:
    metrics = load_csv("model_metrics")
    selected = metrics[
        metrics["module"].eq("Delivery Risk")
        & metrics["selected"].astype(str).str.lower().eq("true")
    ]
    return selected.iloc[0]


def _prediction_form(order_data: pd.DataFrame) -> None:
    st.subheader("Estimate Late Delivery Risk")
    st.caption("This is an estimated probability, not a guarantee of a late arrival.")
    with st.form("delivery_prediction"):
        first, second, third = st.columns(3)
        with first:
            purchase_month = st.selectbox("Purchase month", list(range(1, 13)), index=7)
            purchase_weekday = st.selectbox("Purchase weekday", list(range(7)), format_func=lambda value: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][value])
            purchase_hour = st.slider("Purchase hour", 0, 23, 14)
            customer_state = st.selectbox("Customer state", sorted(order_data["customer_state"].dropna().unique()))
            seller_state = st.selectbox("Seller state", sorted(order_data["seller_state"].dropna().unique()))
            product_category = st.selectbox("Primary category", sorted(order_data["product_category"].dropna().unique()))
        with second:
            item_count = st.number_input("Items", 1, 25, 1)
            product_count = st.number_input("Unique products", 1, 25, 1)
            seller_count = st.number_input("Unique sellers", 1, 10, 1)
            merchandise = st.number_input("Merchandise value (R$)", 0.85, 10000.0, 120.0)
            freight = st.number_input("Freight value (R$)", 0.0, 1000.0, 20.0)
            payment = st.number_input("Amount paid (R$)", 0.0, 15000.0, 140.0)
        with third:
            installments = st.number_input("Maximum installments", 0, 24, 3)
            payment_type = st.selectbox("Dominant payment type", sorted(order_data["dominant_payment_type"].dropna().unique()))
            distance = st.number_input("Approximate distance (km)", 0.0, 5000.0, 500.0)
            estimated_days = st.number_input("Estimated delivery window (days)", 1.0, 90.0, 20.0)
            weight = st.number_input("Average product weight (g)", 0.0, 50000.0, 1200.0)
        submitted = st.form_submit_button("Estimate risk", type="primary")
    if submitted:
        row = pd.DataFrame(
            [
                {
                    "purchase_month": purchase_month,
                    "purchase_weekday": purchase_weekday,
                    "purchase_hour": purchase_hour,
                    "customer_state": customer_state,
                    "seller_state": seller_state,
                    "product_category": product_category,
                    "item_count": item_count,
                    "unique_product_count": product_count,
                    "unique_seller_count": seller_count,
                    "merchandise_revenue": merchandise,
                    "total_freight_value": freight,
                    "gross_order_value": merchandise + freight,
                    "total_payment_value": payment,
                    "maximum_installments": installments,
                    "dominant_payment_type": payment_type,
                    "distance_km": distance,
                    "estimated_delivery_days": estimated_days,
                    "average_product_weight_g": weight,
                }
            ]
        )
        bundle = load_model("delivery_risk.joblib")
        probability = float(bundle["model"].predict_proba(row[bundle["features"]])[:, 1][0])
        category = "Low" if probability < 0.25 else "Medium" if probability < 0.50 else "High"
        st.metric("Estimated Late Delivery Risk", format_percent(probability, 1), category)
        st.caption("Contributing factors are represented by the model-wide importance chart above; it is not a local causal explanation.")


def render() -> None:
    page_header("Delivery Risk", "Chronological test evaluation and pre-outcome risk estimation")
    selected = _selected_delivery_metrics()
    results = load_results()["delivery_risk"]
    metric_row(
        [
            ("Selected Model", str(selected["model"]), "Selected by test F1 with PR-AUC as tie-breaker."),
            ("F1", f"{selected['f1']:.3f}", None),
            ("ROC-AUC", f"{selected['roc_auc']:.3f}", None),
            ("Precision", f"{selected['precision']:.3f}", None),
            ("Recall", f"{selected['recall']:.3f}", None),
        ]
    )
    st.caption(
        f"Chronological test: {results['test_start'][:10]} onward • {results['test_rows']:,} rows • "
        f"late-delivery prevalence {results['positive_rate_test']:.2%}."
    )
    importance = load_parquet("delivery_feature_importance").head(15).sort_values("importance")
    importance["feature"] = (
        importance["feature"].str.replace(r"^(numeric|categorical)__", "", regex=True)
        .str.replace("_", " ").str.title()
    )
    predictions = load_parquet("delivery_predictions")
    confusion = load_parquet("delivery_confusion_matrix")
    left, right = st.columns(2)
    with left:
        figure = px.bar(importance, x="importance", y="feature", orientation="h", title="Model Feature Importance")
        figure.update_traces(marker_color=RISK)
        st.plotly_chart(style_figure(figure, 450), width="stretch")
    with right:
        matrix = confusion.set_index("actual").to_numpy()
        figure = px.imshow(
            matrix,
            text_auto=True,
            x=["Predicted on time", "Predicted late"],
            y=["Actual on time", "Actual late"],
            color_continuous_scale="Blues",
            title="Confusion Matrix",
        )
        st.plotly_chart(style_figure(figure, 450), width="stretch")
    left, right = st.columns(2)
    with left:
        roc = load_parquet("delivery_roc_curve")
        figure = go.Figure()
        figure.add_scatter(x=roc["false_positive_rate"], y=roc["true_positive_rate"], mode="lines", name="Model")
        figure.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="Random", line=dict(dash="dash"))
        figure.update_layout(title="ROC Curve", xaxis_title="False Positive Rate", yaxis_title="True Positive Rate")
        st.plotly_chart(style_figure(figure), width="stretch")
    with right:
        pr = load_parquet("delivery_pr_curve")
        figure = px.line(pr, x="recall", y="precision", title="Precision–Recall Curve")
        st.plotly_chart(style_figure(figure), width="stretch")
    figure = px.histogram(predictions, x="late_delivery_probability", color="risk_category", nbins=40, title="Estimated Risk Distribution")
    st.plotly_chart(style_figure(figure), width="stretch")
    _prediction_form(load_parquet("overview"))
    download_csv(predictions, "Download delivery-risk predictions", "delivery_risk_predictions.csv", "risk_download")
