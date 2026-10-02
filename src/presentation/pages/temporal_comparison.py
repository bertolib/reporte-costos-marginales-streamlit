"""Generation by energy source page."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.settings import GENERATION_EXCEL_PATH
from src.infrastructure.repositories.generation_repository import ENERGY_COLUMNS, GenerationRepository


@st.cache_data(show_spinner="Leyendo generacion por tipo de tecnologia...")
def _load_generation_data(source_path: str) -> pd.DataFrame:
    repository = GenerationRepository(GENERATION_EXCEL_PATH)
    return repository.load_daily_generation()


def render_temporal_comparison(observations: pd.DataFrame) -> None:
    """Render generation by energy source from the generation workbook."""
    st.title("Generación por tipo de energía")

    if not GENERATION_EXCEL_PATH.exists():
        st.error(f"No se encontro el archivo fuente: {GENERATION_EXCEL_PATH.name}")
        return

    generation = _load_generation_data(str(GENERATION_EXCEL_PATH))
    if generation.empty:
        st.warning("No hay datos de generación disponibles.")
        return

    latest_date = generation["date"].max()
    st.caption(f"Datos de generación disponibles hasta el {latest_date.strftime('%d-%m-%Y')}.")

    start_date, end_date = _render_period_filter(generation)
    available_energy = [energy for energy in ENERGY_COLUMNS if energy in generation["energy_type"].unique()]
    selected_energy = st.multiselect(
        "Tipo de energía",
        available_energy,
        default=available_energy,
    )

    filtered = generation[
        (generation["date"] >= pd.Timestamp(start_date))
        & (generation["date"] <= pd.Timestamp(end_date))
        & (generation["energy_type"].isin(selected_energy))
    ].copy()

    if filtered.empty:
        st.warning("No hay datos para los filtros seleccionados.")
        return

    st.plotly_chart(_generation_chart(filtered), width="stretch")


def _render_period_filter(generation: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    min_date = generation["date"].min().date()
    max_date = generation["date"].max().date()
    selected_period = st.date_input(
        "Periodo",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(selected_period, tuple) and len(selected_period) == 2:
        return pd.Timestamp(selected_period[0]), pd.Timestamp(selected_period[1])
    return pd.Timestamp(min_date), pd.Timestamp(max_date)


def _generation_chart(generation: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    style_by_energy = {
        "Carbón": dict(color="#000000", dash="dash"),
        "Cogeneracion": dict(color="#B36B24", dash="dot"),
        "Diésel": dict(color="#FF0000", dash="dot"),
        "Fuel Oil": dict(color="#7F7F7F", dash="dot"),
        "Gas Natural": dict(color="#7F7F7F", dash="dash"),
        "Geotérmica": dict(color="#F2A900"),
        "Solar": dict(color="#FFF200"),
        "Pasada": dict(color="#0070C0"),
        "PetCoke": dict(color="#2F5597", dash="dot"),
        "Embalse": dict(color="#8CCDE0"),
        "Eólica": dict(color="#70AD47"),
        "BioGas": dict(color="#00B050"),
        "Biomasa": dict(color="#76933C"),
        "Térmica": dict(color="#D66060"),
        "Termosolar": dict(color="#9BBB59"),
        "Inyección": dict(color="#8064A2"),
        "Retiro": dict(color="#4BACC6"),
        "-": dict(color="#F4B183", dash="dash"),
        "GLP": dict(color="#2F5597"),
    }

    for energy_type in ENERGY_COLUMNS:
        energy_data = generation[generation["energy_type"] == energy_type]
        if energy_data.empty:
            continue
        style = style_by_energy.get(energy_type, {})
        fig.add_trace(
            go.Scatter(
                x=energy_data["date"],
                y=energy_data["generation_mwh"],
                name=energy_type,
                mode="lines",
                line=dict(width=2, color=style.get("color"), dash=style.get("dash")),
            )
        )

    fig.update_layout(
        template="plotly_white",
        title="Generación por tipo de fuente de energía",
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        legend_title_text="",
        margin=dict(l=10, r=10, t=50, b=110),
        height=540,
        yaxis_title="Generación real (MWh)",
        xaxis_title="",
    )
    return fig
