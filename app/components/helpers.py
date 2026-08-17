"""Dashboard data access, formatting, and error handling."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = ROOT_DIR / "data" / "processed" / "dashboard"
MODEL_DIR = ROOT_DIR / "models"
RESULTS_PATH = ROOT_DIR / "reports" / "model_results" / "pipeline_results.json"


@st.cache_data(show_spinner=False)
def load_parquet(name: str) -> pd.DataFrame:
    path = DASHBOARD_DIR / f"{name}.parquet"
    if not path.exists():
        st.error("Processed data is not available. Run `python run_pipeline.py` before starting the dashboard.")
        st.stop()
    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def load_csv(name: str) -> pd.DataFrame:
    path = DASHBOARD_DIR / f"{name}.csv"
    if not path.exists():
        st.error("Processed data is not available. Run `python run_pipeline.py` before starting the dashboard.")
        st.stop()
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def load_results() -> dict:
    if not RESULTS_PATH.exists():
        st.error("Model results are not available. Run `python run_pipeline.py` first.")
        st.stop()
    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))


@st.cache_resource(show_spinner=False)
def load_model(name: str):
    path = MODEL_DIR / name
    if not path.exists():
        st.error("The trained model is not available. Run `python run_pipeline.py` first.")
        st.stop()
    return joblib.load(path)


def format_brl(value: float, compact: bool = False) -> str:
    if compact:
        absolute = abs(value)
        if absolute >= 1_000_000:
            return f"R$ {value / 1_000_000:.2f}M"
        if absolute >= 1_000:
            return f"R$ {value / 1_000:.1f}K"
    return f"R$ {value:,.2f}"


def format_percent(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}%}"


def download_csv(data: pd.DataFrame, label: str, filename: str, key: str) -> None:
    st.download_button(
        label,
        data.to_csv(index=False).encode("utf-8"),
        filename,
        "text/csv",
        key=key,
    )


def inject_app_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.6rem; padding-bottom: 2.5rem; max-width: 1320px;}
        [data-testid="stMetric"] {background: #f7f9fc; border: 1px solid #e4eaf2; border-radius: 12px; padding: 14px;}
        [data-testid="stMetricLabel"] {color: #526071;}
        h1, h2, h3 {letter-spacing: -0.02em;}
        .page-subtitle {color: #667085; margin-top: -0.6rem; margin-bottom: 1.3rem;}
        .insight-card {background:#f7f9fc; border-left:4px solid #1565c0; border-radius:8px; padding:0.75rem 0.9rem; margin-bottom:0.65rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)
