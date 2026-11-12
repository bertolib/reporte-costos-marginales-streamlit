"""Streamlit application composition."""

import streamlit as st
from httpx import TransportError
from postgrest.exceptions import APIError

from config.settings import APP_TITLE, COMPANY_NAME, DATA_SOURCE, DEFAULT_EXCEL_PATH, SUPABASE_TABLE
from src.domain.enums import Granularity
from src.infrastructure.repositories.excel_market_repository import ExcelMarketRepository
from src.infrastructure.repositories.supabase_market_repository import SupabaseMarketRepository
from src.infrastructure.repositories.snapshot_market_repository import SNAPSHOT_PATH, SnapshotMarketRepository
from src.presentation.components.layout import load_css, render_sidebar_context
from src.presentation.pages.executive_dashboard import render_executive_dashboard
from src.presentation.pages.data_detail import render_data_detail
from src.presentation.pages.marginal_costs import render_marginal_costs


def _repository(source_token: str = ""):
    if source_token.startswith("snapshot:"):
        return SnapshotMarketRepository()
    if DATA_SOURCE == "supabase":
        return SupabaseMarketRepository(SUPABASE_TABLE)
    return ExcelMarketRepository(DEFAULT_EXCEL_PATH)


def _source_label() -> str:
    if DATA_SOURCE == "supabase":
        return f"supabase:{SUPABASE_TABLE}"
    return str(DEFAULT_EXCEL_PATH)


def _source_token() -> str:
    if DATA_SOURCE == "supabase":
        latest_timestamp = _repository().get_last_update()
        return f"{SUPABASE_TABLE}:supabase:{latest_timestamp}"
    if DEFAULT_EXCEL_PATH.exists():
        return f"{DEFAULT_EXCEL_PATH}:{DEFAULT_EXCEL_PATH.stat().st_mtime}"
    return f"{DEFAULT_EXCEL_PATH}:missing"


@st.cache_data(ttl=300, max_entries=2, show_spinner="Leyendo datos horarios...")
def _load_hourly_data(source_token: str):
    repository = _repository(source_token)
    return repository.load_observations(Granularity.HOURLY)


@st.cache_data(ttl=300, max_entries=2, show_spinner="Leyendo datos quinceminutales...")
def _load_fifteen_minutes_data(source_token: str):
    repository = _repository(source_token)
    return repository.load_observations(Granularity.FIFTEEN_MINUTES)


def _actual_only(observations):
    if "scenario" not in observations.columns:
        return observations
    return observations[observations["scenario"] == "actual"].copy()


def _load_report_data(include_detail: bool):
    """Use a dated, explicit backup only when the configured database fails."""
    use_snapshot = False
    try:
        source_token = _source_token()
        hourly = _load_hourly_data(source_token)
        detail = _load_fifteen_minutes_data(source_token) if include_detail else None
    except (TransportError, APIError):
        if DATA_SOURCE != "supabase" or not SNAPSHOT_PATH.exists():
            raise
        use_snapshot = True
        source_token = f"snapshot:{SNAPSHOT_PATH.stat().st_mtime_ns}"
        hourly = _load_hourly_data(source_token)
        detail = _load_fifteen_minutes_data(source_token) if include_detail else None
    return _actual_only(hourly), detail, use_snapshot


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

    if DATA_SOURCE != "supabase" and not DEFAULT_EXCEL_PATH.exists():
        st.error(f"No se encontro el archivo fuente: {DEFAULT_EXCEL_PATH}")
        return

    observations, detail, use_snapshot = _load_report_data(page == "Detalle de los Datos")
    source_label = "Respaldo verificado" if use_snapshot else _source_label()
    st.sidebar.caption(f"Fuente de costos marginales: {source_label}")
    if use_snapshot:
        latest = observations["timestamp"].max().strftime("%d-%m-%Y")
        st.warning(
            f"La conexión con la base de datos no está disponible. "
            f"Se muestra el último respaldo verificado, con datos hasta el {latest}."
        )

    if page == "Resumen General":
        render_executive_dashboard(observations)
    elif page == "Contexto Mercado Electrico":
        render_marginal_costs(observations)
    elif page == "Detalle de los Datos":
        render_data_detail(
            observations,
            _actual_only(detail),
        )

    if page != "Contexto Mercado Electrico":
        mode_caption = "Modo actual: Supabase" if DATA_SOURCE == "supabase" else "Modo actual: Excel read-only"
        if use_snapshot:
            mode_caption = "Modo actual: respaldo verificado (sin conexión)"
        render_sidebar_context(observations, source_label, mode_caption=mode_caption)
