"""Plotly styling shared across dashboard pages."""

from __future__ import annotations

import plotly.graph_objects as go


PRIMARY = "#1565c0"
ACCENT = "#00a6a6"
WARNING = "#f59e0b"
RISK = "#dc2626"


def style_figure(figure: go.Figure, height: int = 390) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=55, b=25),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(color="#253142"),
        legend_title_text="",
        hoverlabel=dict(bgcolor="white"),
    )
    figure.update_xaxes(showgrid=False)
    figure.update_yaxes(gridcolor="#edf1f7", zeroline=False)
    return figure
