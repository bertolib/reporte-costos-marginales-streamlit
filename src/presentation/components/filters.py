"""Reusable filter controls."""

import pandas as pd
import streamlit as st

from src.analytics.aggregations import filter_period


MONTH_NAMES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def render_market_filters(
    observations: pd.DataFrame,
    key_prefix: str,
    default_node_names: list[str] | None = None,
    default_actual_only: bool = True,
) -> pd.DataFrame:
    """Render common filters and return filtered observations."""
    if observations.empty:
        return observations

    with st.sidebar.container(key=f"{key_prefix}_filters_bar"):
        st.subheader("Filtros")
        nodes = sorted(observations["node_name"].dropna().unique())
        node_options = _node_options(observations, nodes)
        scenarios = sorted(observations["scenario"].dropna().unique()) if "scenario" in observations.columns else []
        selected_scenarios = ["actual"] if "actual" in scenarios else scenarios
        default_scenarios = ["actual"] if default_actual_only and "actual" in scenarios else scenarios
        default_scope = observations[observations["scenario"].isin(default_scenarios)]
        if default_scope.empty:
            default_scope = observations

        min_date = default_scope["timestamp"].min().date()
        max_date = default_scope["timestamp"].max().date()
        default_start = max(min_date, (pd.Timestamp(max_date) - pd.Timedelta(days=30)).date())
        default_nodes = default_node_names or nodes
        default_nodes = [node for node in default_nodes if node in nodes] or nodes
        default_node_labels = [_node_label(node, observations) for node in default_nodes]

        period_options = _build_period_options(default_scope)
        selected_period = st.selectbox(
            "Periodo",
            options=list(period_options.keys()),
            index=0,
            key=f"{key_prefix}_period",
        )

        if selected_period == "Personalizado":
            start_date = st.date_input("Desde", value=default_start, key=f"{key_prefix}_start")
            end_date = st.date_input("Hasta", value=max_date, key=f"{key_prefix}_end")
            invalid_period = pd.Timestamp(start_date) > pd.Timestamp(end_date)
            if invalid_period:
                st.error("Periodo invalido: la fecha Desde no puede ser posterior a la fecha Hasta.")
        else:
            start_date, end_date = period_options[selected_period]
            invalid_period = False
            st.caption(f"Rango: {start_date:%d-%m-%Y} a {end_date:%d-%m-%Y}")

        selected_node_labels = st.multiselect(
            "Barras",
            options=list(node_options.keys()),
            default=default_node_labels,
            key=f"{key_prefix}_nodes",
        )
        st.caption("Zonas: N = Norte, C = Centro, S = Sur.")
        selected_nodes = [node_options[label] for label in selected_node_labels]

    if invalid_period:
        st.error("Corrige el rango de fechas para visualizar la informacion.")
        st.stop()

    return filter_period(
        observations=observations,
        start_date=pd.Timestamp(start_date),
        end_date=pd.Timestamp(end_date),
        nodes=selected_nodes,
        zones=None,
        scenarios=selected_scenarios,
    )


def _build_period_options(observations: pd.DataFrame) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    if observations.empty:
        today = pd.Timestamp.today().normalize()
        return {"Personalizado": (today, today)}

    max_timestamp = observations["timestamp"].max()
    min_timestamp = observations["timestamp"].min()
    max_date = max_timestamp.normalize()
    min_date = min_timestamp.normalize()
    custom_range = (max(max_date - pd.Timedelta(days=30), min_date), max_date)
    options: dict[str, tuple[pd.Timestamp, pd.Timestamp]] = {
        "Personalizado": custom_range,
        "Ultimos 30 dias": (max(max_date - pd.Timedelta(days=30), min_date), max_date),
        "Ultimos 7 dias": (max(max_date - pd.Timedelta(days=7), min_date), max_date),
    }

    months = observations["timestamp"].dt.to_period("M").drop_duplicates().sort_values(ascending=False)
    for month_period in months:
        start = month_period.to_timestamp()
        end = min((start + pd.offsets.MonthEnd(0)).normalize(), max_date)
        label = f"{MONTH_NAMES[start.month]} {start.year}"
        options[label] = (start, end)

    return options


def _node_options(observations: pd.DataFrame, nodes: list[str]) -> dict[str, str]:
    return {_node_label(node, observations): node for node in nodes}


def _node_label(node_name: str, observations: pd.DataFrame) -> str:
    zone = observations.loc[observations["node_name"] == node_name, "zone"].dropna()
    suffix = _zone_suffix(zone.iloc[0] if not zone.empty else "")
    return f"{node_name} - {suffix}" if suffix else node_name


def _zone_suffix(zone: str) -> str:
    return {
        "Norte": "N",
        "Centro": "C",
        "Sur": "S",
    }.get(zone, "")
