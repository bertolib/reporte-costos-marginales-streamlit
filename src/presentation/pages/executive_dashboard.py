"""Executive dashboard page."""

import pandas as pd
import streamlit as st

from src.analytics.aggregations import daily_bess_arbitrage
from src.application.services.insight_service import InsightService
from src.application.services.kpi_service import KpiService
from config.settings import APP_TITLE
from src.presentation.components.charts import (
    bess_arbitrage_chart,
    daily_trend_chart,
    hourly_profile_chart,
    last_six_months_average_chart,
)
from src.presentation.components.filters import render_market_filters
from src.presentation.components.layout import format_delta, render_kpi_grid


def render_executive_dashboard(observations: pd.DataFrame) -> None:
    """Render executive overview."""
    st.title(APP_TITLE)
    st.caption("Seguimiento de costos marginales del Sistema Electrico Nacional")

    filtered = render_market_filters(
        observations,
        "executive",
        default_node_names=["Mejillones 110"],
    )
    kpis = KpiService().build_executive_kpis(filtered)

    render_kpi_grid(
        [
            ("Promedio", f"{kpis.average_cost:,.2f}", "USD/MWh"),
            ("Maximo", f"{kpis.max_cost:,.2f}", "USD/MWh"),
            ("Minimo", f"{kpis.min_cost:,.2f}", "USD/MWh"),
            ("Var. semanal", format_delta(kpis.weekly_variation_pct), None),
            _monthly_variation_kpi(filtered, kpis.monthly_variation_pct),
            ("Registros", f"{kpis.observations:,}", None),
        ]
    )

    st.subheader("Principales Hitos")
    insights = InsightService().build_initial_insights(filtered)
    for insight in insights:
        st.markdown(f"<div class='executive-note'>{insight}</div>", unsafe_allow_html=True)

    st.subheader("Tendencia diaria")
    st.plotly_chart(daily_trend_chart(filtered), width="stretch")

    st.subheader(_last_six_months_title(filtered))
    st.plotly_chart(last_six_months_average_chart(_build_last_six_months_scope(observations, filtered), _period_end(filtered)), width="stretch")

    st.subheader("Perfil horario")
    st.plotly_chart(hourly_profile_chart(filtered), width="stretch")

    st.subheader("Spread Carga/Descarga")
    arbitrage = daily_bess_arbitrage(filtered)
    st.plotly_chart(bess_arbitrage_chart(filtered), width="stretch")
    if arbitrage.empty:
        render_kpi_grid(
            [
                ("Spread promedio diario", "s/i", "USD/MWh"),
                ("Spread maximo del periodo", "s/i", "USD/MWh"),
                ("Dias sobre percentil 75", "0", None),
            ]
        )
    else:
        spread_p75 = arbitrage["spread"].quantile(0.75)
        days_above_p75 = arbitrage[arbitrage["spread"] > spread_p75]["date"].nunique()
        render_kpi_grid(
            [
                ("Spread promedio diario", f"{arbitrage['spread'].mean():,.2f}", "USD/MWh"),
                ("Spread maximo del periodo", f"{arbitrage['spread'].max():,.2f}", "USD/MWh"),
                (f"Dias sobre percentil 75 ({spread_p75:,.2f} USD/MWh)", f"{days_above_p75:,}", None),
            ]
        )


def _period_end(filtered: pd.DataFrame) -> pd.Timestamp | None:
    if filtered.empty:
        return None
    return filtered["timestamp"].max()


def _monthly_variation_label(filtered: pd.DataFrame) -> str:
    if filtered.empty:
        return "Var. mensual"
    current_month = filtered["timestamp"].max().to_period("M").to_timestamp()
    previous_month = current_month - pd.DateOffset(months=1)
    return f"Var. mensual ({_month_label(current_month)} vs {_month_label(previous_month)})"


def _monthly_variation_kpi(
    filtered: pd.DataFrame,
    monthly_variation_pct: float | None,
) -> tuple[str, str, str | None]:
    if monthly_variation_pct is None:
        return ("Var. mensual", "", "No aplica al periodo. Comparacion entre meses.")
    return (_monthly_variation_label(filtered), format_delta(monthly_variation_pct), None)


def _month_label(month: pd.Timestamp) -> str:
    month_names = {
        1: "ene",
        2: "feb",
        3: "mar",
        4: "abr",
        5: "may",
        6: "jun",
        7: "jul",
        8: "ago",
        9: "sept",
        10: "oct",
        11: "nov",
        12: "dic",
    }
    timestamp = pd.Timestamp(month)
    return f"{month_names[timestamp.month]}-{timestamp.strftime('%y')}"


def _last_six_months_title(filtered: pd.DataFrame) -> str:
    title = "Promedio ultimos 6 meses"
    selected_nodes = filtered["node_name"].dropna().unique()
    if len(selected_nodes) == 1:
        return f"{title} - {selected_nodes[0]}"
    return title


def _build_last_six_months_scope(observations: pd.DataFrame, filtered: pd.DataFrame) -> pd.DataFrame:
    """Keep selected bars/zones, but expand the date window to six months ending in the selected period."""
    if filtered.empty:
        return filtered

    period_end = filtered["timestamp"].max()
    end_month = period_end.to_period("M").to_timestamp()
    first_month = end_month - pd.DateOffset(months=5)
    selected_nodes = filtered["node_name"].dropna().unique()
    selected_zones = filtered["zone"].dropna().unique()
    return observations[
        (observations["timestamp"] >= first_month)
        & (observations["timestamp"] <= period_end.normalize() + pd.Timedelta(days=1) - pd.Timedelta(seconds=1))
        & (observations["node_name"].isin(selected_nodes))
        & (observations["zone"].isin(selected_zones))
    ]
