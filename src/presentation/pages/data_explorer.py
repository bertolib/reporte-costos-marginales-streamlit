"""Data explorer page."""

import pandas as pd
import streamlit as st

from src.presentation.components.filters import render_market_filters


def render_data_explorer(observations: pd.DataFrame) -> None:
    """Render data explorer with filters and export-ready table."""
    st.title("Explorador de Datos")
    st.caption("Consulta tabular del modelo canónico normalizado desde el Excel fuente.")

    filtered = render_market_filters(observations, "explorer")
    display = filtered.sort_values("timestamp", ascending=False).copy()
    if "timestamp" in display.columns:
        display["timestamp"] = display["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    display = display.drop(columns=["scenario"], errors="ignore")
    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
    )
    csv = display.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Descargar CSV",
        data=csv,
        file_name="costos_marginales_filtrados.csv",
        mime="text/csv",
    )
