"""Model leakage, persistence, forecast, notebook, and app smoke tests."""

import importlib
import json
import subprocess
import sys

import joblib
import pandas as pd
from streamlit.testing.v1 import AppTest

from src.config import DELIVERY_MODEL_FEATURES, MODEL_DIR, POST_OUTCOME_COLUMNS, ROOT_DIR
from src.data.validate_data import assert_columns_excluded
from src.models.delivery_risk import build_delivery_training_data
from src.models.forecasting import detect_complete_months


def test_delivery_features_have_no_outcome_leakage():
    assert_columns_excluded(DELIVERY_MODEL_FEATURES, POST_OUTCOME_COLUMNS)


def test_delivery_training_target_not_in_features():
    order_level = pd.read_parquet(ROOT_DIR / "data" / "processed" / "core" / "order_level.parquet")
    features, target, identifiers = build_delivery_training_data(order_level)
    assert "late_delivery" not in features.columns
    assert len(features) == len(target) == len(identifiers)


def test_delivery_model_reloads_and_scores():
    bundle = joblib.load(MODEL_DIR / "delivery_risk.joblib")
    order_level = pd.read_parquet(ROOT_DIR / "data" / "processed" / "core" / "order_level.parquet")
    features, _, _ = build_delivery_training_data(order_level.head(5000))
    probability = bundle["model"].predict_proba(features[bundle["features"]].head(3))[:, 1]
    assert ((probability >= 0) & (probability <= 1)).all()


def test_segmentation_model_reloads():
    bundle = joblib.load(MODEL_DIR / "segmentation.joblib")
    assert bundle["features"] == ["recency", "frequency", "monetary"]


def test_forecast_model_reloads():
    bundle = joblib.load(MODEL_DIR / "sales_forecast.joblib")
    assert bundle["future_horizon"] == 6


def test_forecast_completeness_excludes_sparse_tail():
    monthly = pd.read_parquet(ROOT_DIR / "data" / "processed" / "dashboard" / "monthly_sales.parquet")
    complete, partial = detect_complete_months(monthly)
    assert complete["purchase_period"].max() == pd.Timestamp("2018-08-01")
    assert len(partial) == 2


def test_notebooks_are_valid_json_and_have_no_stored_outputs():
    for path in (ROOT_DIR / "notebooks").glob("*.ipynb"):
        notebook = json.loads(path.read_text(encoding="utf-8"))
        assert notebook["nbformat"] == 4
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                assert cell["outputs"] == []


def test_all_dashboard_page_modules_import():
    modules = [
        "overview", "sales_analytics", "customer_analytics", "segmentation",
        "delivery_risk", "retention_analysis", "forecasting", "product_analytics",
        "delivery_satisfaction", "model_performance",
    ]
    for name in modules:
        importlib.import_module(f"app.pages.{name}")


def test_main_application_imports_without_running_server():
    module = importlib.import_module("app.app")
    assert callable(module.main)


def test_streamlit_entrypoint_can_load_when_named_app():
    command = """
import importlib.util
import sys
from pathlib import Path

path = Path('app/app.py').resolve()
spec = importlib.util.spec_from_file_location('app', path)
module = importlib.util.module_from_spec(spec)
sys.modules['app'] = module
spec.loader.exec_module(module)
assert callable(module.main)
"""
    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_streamlit_application_executes_without_exception():
    application = AppTest.from_file(str(ROOT_DIR / "app" / "app.py")).run(timeout=30)
    assert len(application.exception) == 0
