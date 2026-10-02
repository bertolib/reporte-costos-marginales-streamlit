"""Shared Streamlit layout helpers."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


def load_css() -> None:
    """Load custom CSS."""
    css_path = Path(__file__).resolve().parents[1] / "styles" / "main.css"
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def render_sidebar_context(
    observations: pd.DataFrame | None,
    source_path: Path | str,
    latest_date: pd.Timestamp | None = None,
    latest_label: str = "Ultimo dato con informacion",
    mode_caption: str = "Modo actual: Excel read-only",
) -> None:
    """Render source and update context in sidebar."""
    if latest_date is None and observations is not None:
        actual = observations[observations["scenario"] == "actual"]
        latest_date = actual["timestamp"].max() if not actual.empty else None
    is_file_source = isinstance(source_path, Path)
    file_updated = datetime.fromtimestamp(source_path.stat().st_mtime) if is_file_source and source_path.exists() else None
    source_name = source_path.name if is_file_source else source_path
    st.sidebar.divider()
    st.sidebar.caption("Fuente de datos")
    st.sidebar.write(source_name)
    if file_updated is not None:
        st.sidebar.metric("Ultima actualizacion del archivo", file_updated.strftime("%d-%m-%Y"))
    if latest_date is not None:
        st.sidebar.metric(latest_label, latest_date.strftime("%d-%m-%Y"))
    st.sidebar.caption(mode_caption)


def format_delta(value: float | None) -> str:
    """Format percentage deltas for KPI cards."""
    if value is None:
        return "s/i"
    return f"{value:+.1f}%"


def render_kpi_grid(items: list[tuple[str, str, str | None]]) -> None:
    """Render responsive KPI cards without truncating values on small monitors."""
    cards = []
    for label, value, suffix in items:
        if not value and suffix:
            value_html = f"<div class='kpi-note'>{suffix}</div>"
        else:
            suffix_html = f"<span>{suffix}</span>" if suffix else ""
            value_html = f"<div class='kpi-value'>{value}{suffix_html}</div>"
        cards.append(
            "<div class='kpi-card'>"
            f"<div class='kpi-label'>{label}</div>"
            f"{value_html}"
            "</div>"
        )
    st.markdown(f"<div class='kpi-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)
