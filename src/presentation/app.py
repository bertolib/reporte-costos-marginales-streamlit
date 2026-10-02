"""Streamlit application composition."""

import streamlit as st

from config.settings import APP_TITLE, COMPANY_NAME, DATA_SOURCE, DEFAULT_EXCEL_PATH, SUPABASE_TABLE
from src.domain.enums import Granularity
from src.infrastructure.repositories.excel_market_repository import ExcelMarketRepository
from src.infrastructure.repositories.supabase_market_repository import SupabaseMarketRepository
from src.presentation.components.layout import load_css, render_sidebar_context
from src.presentation.pages.executive_dashboard import render_executive_dashboard
from src.presentation.pages.data_detail import render_data_detail
from src.presentation.pages.marginal_costs import render_marginal_costs


def _repository():
    if DATA_SOURCE == "supabase":
        return SupabaseMarketRepository(SUPABASE_TABLE)
    return ExcelMarketRepository(DEFAULT_EXCEL_PATH)


def _source_label() -> str:
    if DATA_SOURCE == "supabase":
        return f"supabase:{SUPABASE_TABLE}"
    return str(DEFAULT_EXCEL_PATH)


def _source_token() -> str:
    if DATA_SOURCE == "supabase":
        return f"{SUPABASE_TABLE}:supabase"
    if DEFAULT_EXCEL_PATH.exists():
        return f"{DEFAULT_EXCEL_PATH}:{DEFAULT_EXCEL_PATH.stat().st_mtime}"
    return f"{DEFAULT_EXCEL_PATH}:missing"


@st.cache_data(show_spinner="Leyendo datos horarios...")
def _load_hourly_data(source_token: str):
    repository = _repository()
    return repository.load_observations(Granularity.HOURLY)


@st.cache_data(show_spinner="Leyendo datos quinceminutales...")
def _load_fifteen_minutes_data(source_token: str):
    repository = _repository()
    return repository.load_observations(Granularity.FIFTEEN_MINUTES)


def _actual_only(observations):
    if "scenario" not in observations.columns:
        return observations
    return observations[observations["scenario"] == "actual"].copy()


def run_app() -> None:
    """Run Streamlit app."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=":material/electric_bolt:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    load_css()

    st.sidebar.title(APP_TITLE)
    st.sidebar.caption(COMPANY_NAME)
    page = st.sidebar.radio(
        "Navegacion",
        [
            "Resumen General",
            "Contexto Mercado Electrico",
            "Detalle de los Datos",
        ],
    )
    st.sidebar.caption(f"Fuente de costos marginales: {_source_label()}")

    if DATA_SOURCE != "supabase" and not DEFAULT_EXCEL_PATH.exists():
        st.error(f"No se encontro el archivo fuente: {DEFAULT_EXCEL_PATH}")
        return

    source_token = _source_token()
    observations = _actual_only(_load_hourly_data(source_token))

    if page == "Resumen General":
        render_executive_dashboard(observations)
    elif page == "Contexto Mercado Electrico":
        render_marginal_costs(observations)
    elif page == "Detalle de los Datos":
        render_data_detail(
            observations,
            _actual_only(_load_fifteen_minutes_data(source_token)),
        )

    if page != "Contexto Mercado Electrico":
        mode_caption = "Modo actual: Supabase" if DATA_SOURCE == "supabase" else "Modo actual: Excel read-only"
        render_sidebar_context(observations, _source_label(), mode_caption=mode_caption)
