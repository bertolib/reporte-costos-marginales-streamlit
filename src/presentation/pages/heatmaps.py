"""Heatmap page."""

import pandas as pd
import streamlit as st

from src.presentation.components.charts import node_heatmap
from src.presentation.components.filters import render_market_filters


def render_heatmaps(observations: pd.DataFrame) -> None:
    """Render hour-by-date heatmap."""
    st.title("Heatmaps")
    st.caption("Mapa de calor hora vs fecha para detectar bloques críticos y cambios de patrón.")

    filtered = render_market_filters(observations, "heatmap")
    nodes = sorted(filtered["node_name"].dropna().unique())
    if not nodes:
        st.warning("No hay datos para los filtros seleccionados.")
        return
    selected_node = st.selectbox("Barra para heatmap", nodes)
    st.plotly_chart(node_heatmap(filtered, selected_node), width="stretch")
