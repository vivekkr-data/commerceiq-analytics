"""Consistent KPI card rows."""

from collections.abc import Sequence

import streamlit as st


def metric_row(metrics: Sequence[tuple[str, str, str | None]]) -> None:
    per_row = len(metrics) if len(metrics) <= 4 else 3
    for start in range(0, len(metrics), per_row):
        row = metrics[start : start + per_row]
        columns = st.columns(per_row)
        for column, (label, value, help_text) in zip(columns, row):
            column.metric(label, value, help=help_text)
