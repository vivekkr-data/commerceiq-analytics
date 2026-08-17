"""Filesystem helpers."""

from src.config import CORE_DIR, DASHBOARD_DIR, EXPORT_DIR, MODEL_DIR, MODEL_RESULTS_DIR


def ensure_output_directories() -> None:
    for directory in [CORE_DIR, DASHBOARD_DIR, EXPORT_DIR, MODEL_DIR, MODEL_RESULTS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
