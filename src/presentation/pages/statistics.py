"""Statistics page."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics.statistics import describe_costs, detect_iqr_outliers
from src.presentation.components.filters import render_market_filters


def _format_period(data: pd.DataFrame) -> str:
    """Return the visible date range for a filtered data set."""
    if data.empty:
        return "sin datos para el periodo seleccionado"
    start = data["timestamp"].min().strftime("%d-%m-%Y")
    end = data["timestamp"].max().strftime("%d-%m-%Y")
    return f"periodo: {start} a {end}"


def render_statistics(observations: pd.DataFrame) -> None:
    """Render statistical analysis page."""
    st.title("Estadísticas")

    filtered = render_market_filters(observations, "stats")
    period_text = _format_period(filtered)

    st.markdown(
        f"""
        <div class="period-label">
          <span>Distribución, percentiles y outliers por barra.</span>
          <strong>Periodo tabla: {period_text.replace("periodo: ", "")}</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )
    summary = describe_costs(filtered)
    st.dataframe(summary, width="stretch", hide_index=True)

    st.markdown(
        f"""
        <div class="period-label">
          <span>Distribución visual por barra.</span>
          <strong>Periodo gráfico: {period_text.replace("periodo: ", "")}</strong>
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

    outliers = detect_iqr_outliers(filtered)
    st.subheader("Outliers detectados")
    st.caption(f"Outliers calculados con {period_text}.")
    st.dataframe(
        outliers[["timestamp", "node_name", "zone", "value", "threshold_low", "threshold_high"]]
        .sort_values("timestamp", ascending=False)
        .head(200),
        width="stretch",
        hide_index=True,
    )
