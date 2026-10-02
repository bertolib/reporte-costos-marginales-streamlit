"""Detailed data page that consolidates statistics, heatmaps and tables."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics.aggregations import filter_period
from src.analytics.statistics import describe_costs, detect_iqr_outliers
from src.presentation.components.charts import node_heatmap
from src.presentation.components.filters import render_market_filters


def render_data_detail(hourly_observations: pd.DataFrame, fifteen_minute_observations: pd.DataFrame) -> None:
    """Render detailed data sections in a single page."""
    st.title("Detalle de los Datos")
    st.caption("Estadísticas, heatmaps, tabla de datos y outliers para revisar la evidencia del periodo.")

    filtered_hourly = render_market_filters(hourly_observations, "detail")
    filtered_fifteen = _align_fifteen_minute_data(fifteen_minute_observations, filtered_hourly)

    _render_statistics_section(filtered_hourly)
    st.divider()
    _render_heatmap_section(filtered_hourly)
    st.divider()
    _render_explorer_section(filtered_fifteen)
    st.divider()
    _render_outliers_section(filtered_hourly)


def _format_period(data: pd.DataFrame) -> str:
    """Return visible date range for a filtered data set."""
    if data.empty:
        return "sin datos para el periodo seleccionado"
    start = data["timestamp"].min().strftime("%d-%m-%Y")
    end = data["timestamp"].max().strftime("%d-%m-%Y")
    return f"{start} a {end}"


def _align_fifteen_minute_data(fifteen_minute_observations: pd.DataFrame, filtered_hourly: pd.DataFrame) -> pd.DataFrame:
    """Apply the same visible period and node selection to 15-minute observations."""
    if filtered_hourly.empty or fifteen_minute_observations.empty:
        return fifteen_minute_observations.iloc[0:0].copy()

    selected_nodes = sorted(filtered_hourly["node_name"].dropna().unique())
    selected_zones = sorted(filtered_hourly["zone"].dropna().unique())
    return filter_period(
        observations=fifteen_minute_observations,
        start_date=filtered_hourly["timestamp"].min().normalize(),
        end_date=filtered_hourly["timestamp"].max().normalize(),
        nodes=selected_nodes,
        zones=selected_zones,
        scenarios=["actual"] if "scenario" in fifteen_minute_observations.columns else None,
    )


def _render_statistics_section(filtered: pd.DataFrame) -> None:
    """Render summary statistics and distribution chart."""
    st.header("Estadísticas")
    period = _format_period(filtered)
    st.markdown(
        f"""
        <div class="period-label">
          <span>Distribución, percentiles y outliers por barra.</span>
          <strong>Periodo tabla: {period}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(describe_costs(filtered), width="stretch", hide_index=True)

    st.markdown(
        f"""
        <div class="period-label">
          <span>Distribución visual por barra.</span>
          <strong>Periodo gráfico: {period}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    fig = px.box(
        filtered,
        x="node_name",
        y="value",
        color="zone",
        points="outliers",
        labels={"node_name": "Barra", "value": "USD/MWh", "zone": "Zona"},
        template="plotly_white",
    )
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=420)
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "El gráfico muestra cómo se distribuyen los costos marginales de cada barra en el periodo. "
        "La línea dentro de cada caja es la mediana; la caja concentra el rango habitual de valores; "
        "los puntos fuera de la caja son valores atípicos o episodios de costos especialmente altos o bajos."
    )


def _render_heatmap_section(filtered: pd.DataFrame) -> None:
    """Render heatmap after the statistical distribution."""
    st.header("Heatmaps")
    st.caption("Mapa de calor hora vs fecha para detectar bloques críticos y cambios de patrón.")
    nodes = sorted(filtered["node_name"].dropna().unique())
    if not nodes:
        st.warning("No hay datos para los filtros seleccionados.")
        return

    default_index = nodes.index("Mejillones 110") if "Mejillones 110" in nodes else 0
    selected_node = st.selectbox("Barra para heatmap", nodes, index=default_index, key="detail_heatmap_node")
    st.plotly_chart(node_heatmap(filtered, selected_node), width="stretch")


def _render_explorer_section(filtered: pd.DataFrame) -> None:
    """Render the tabular explorer."""
    st.header("Explorador de Datos")
    st.caption("Consulta tabular del modelo canónico normalizado desde el Excel fuente.")

    display = filtered.sort_values("timestamp", ascending=False).copy()
    if "timestamp" in display.columns:
        display["timestamp"] = display["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    display = display.drop(columns=["scenario"], errors="ignore")
    st.dataframe(display, width="stretch", hide_index=True)
    csv = display.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Descargar CSV",
        data=csv,
        file_name="costos_marginales_filtrados.csv",
        mime="text/csv",
        key="detail_download_csv",
    )


def _render_outliers_section(filtered: pd.DataFrame) -> None:
    """Render outliers at the end of the detailed page."""
    st.header("Outliers detectados")
    period = _format_period(filtered)
    st.caption(f"Outliers calculados con periodo: {period}.")
    outliers = detect_iqr_outliers(filtered)
    st.dataframe(
        outliers[["timestamp", "node_name", "zone", "value", "threshold_low", "threshold_high"]]
        .sort_values("timestamp", ascending=False)
        .head(200),
        width="stretch",
        hide_index=True,
    )
