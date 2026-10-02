"""Electric-market context page."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.settings import DEFAULT_EXCEL_PATH, GENERATION_EXCEL_PATH
from src.analytics.aggregations import monthly_average
from src.infrastructure.repositories.excel_market_repository import ExcelMarketRepository
from src.infrastructure.repositories.generation_repository import ENERGY_COLUMNS, GenerationRepository
from src.presentation.components.charts import daily_cmg_history_chart, monthly_cmg_coal_chart
from src.presentation.components.layout import render_kpi_grid
from src.presentation.pages.temporal_comparison import _generation_chart


MONTH_LABELS = {
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

MONTH_NUMBERS = {label: number for number, label in MONTH_LABELS.items()}


@st.cache_data(show_spinner="Leyendo generación por tipo de tecnología...")
def _load_generation_data(source_path: str, source_mtime: float) -> pd.DataFrame:
    repository = GenerationRepository(GENERATION_EXCEL_PATH)
    return repository.load_daily_generation()


@st.cache_data(show_spinner="Leyendo hoja CMg Diario...")
def _load_daily_context(source_path: str, source_mtime: float) -> pd.DataFrame:
    repository = ExcelMarketRepository(DEFAULT_EXCEL_PATH)
    return repository.load_daily_market_context()


@st.cache_data(show_spinner="Leyendo tabla Proyecciones CEN...")
def _load_cen_projections(source_path: str, source_mtime: float) -> pd.DataFrame:
    repository = ExcelMarketRepository(DEFAULT_EXCEL_PATH)
    return repository.load_cen_projections()


def render_marginal_costs(observations: pd.DataFrame) -> None:
    """Render generation, marginal-cost and projection context."""
    st.title("Contexto Mercado Electrico")

    _render_generation_section()

    excel_mtime = DEFAULT_EXCEL_PATH.stat().st_mtime
    daily_context = _load_daily_context(str(DEFAULT_EXCEL_PATH), excel_mtime)
    cen_projections = _load_cen_projections(str(DEFAULT_EXCEL_PATH), excel_mtime)

    st.subheader("Cmg promedio historico mensual")
    st.caption(_monthly_context_caption(daily_context))
    st.plotly_chart(monthly_cmg_coal_chart(daily_context), width="stretch")

    st.subheader("Cmg promedio diario 2023 - 2026")
    st.caption(_daily_context_caption(daily_context))
    st.plotly_chart(daily_cmg_history_chart(daily_context), width="stretch")

    st.subheader("Proyecciones CEN")
    st.caption(_projection_context_caption(cen_projections))
    render_kpi_grid(_latest_projection_cards(cen_projections))
    st.dataframe(
        _format_projection_table(cen_projections),
        width="stretch",
        hide_index=True,
    )
    st.subheader("Evolución de las proyecciones de Costo Marginal del CEN")
    st.caption("Revisión de las estimaciones según horizonte de anticipación")
    evolution = _build_cen_projection_evolution(cen_projections)
    if evolution.empty:
        st.warning("No hay datos suficientes para construir la evolución de proyecciones CEN.")
    else:
        actual_mejillones = _build_mejillones_actual_monthly_average(observations)
        selected_targets = _render_cen_target_month_filter(evolution, actual_mejillones)
        filtered_evolution = evolution[evolution["target_label"].isin(selected_targets)]
        if filtered_evolution.empty:
            st.warning("Selecciona al menos un mes objetivo para visualizar el grafico.")
        else:
            st.plotly_chart(_cen_projection_evolution_chart(filtered_evolution, actual_mejillones), width="stretch")


def _render_generation_section() -> None:
    st.subheader("Generación por tipo de energía")

    if not GENERATION_EXCEL_PATH.exists():
        st.error(f"No se encontro el archivo fuente: {GENERATION_EXCEL_PATH.name}")
        return

    generation_mtime = GENERATION_EXCEL_PATH.stat().st_mtime
    generation = _load_generation_data(str(GENERATION_EXCEL_PATH), generation_mtime)
    if generation.empty:
        st.warning("No hay datos de generación disponibles.")
        return

    latest_date = generation["date"].max()
    st.caption(f"Datos de generación disponibles hasta el {latest_date.strftime('%d-%m-%Y')}.")

    start_date, end_date = _render_generation_period_filter(generation)
    available_energy = [energy for energy in ENERGY_COLUMNS if energy in generation["energy_type"].unique()]
    selected_energy = st.multiselect(
        "Tipo de energía",
        available_energy,
        default=available_energy,
        key="context_energy_types",
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


def _render_generation_period_filter(generation: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    min_date = generation["date"].min().date()
    max_date = generation["date"].max().date()
    selected_period = st.date_input(
        "Periodo",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="context_generation_period",
    )
    if isinstance(selected_period, tuple) and len(selected_period) == 2:
        return pd.Timestamp(selected_period[0]), pd.Timestamp(selected_period[1])
    return pd.Timestamp(min_date), pd.Timestamp(max_date)


def _format_projection_table(projections: pd.DataFrame) -> pd.DataFrame:
    display = projections.rename(columns={"projection_month": ""}).copy()
    for column in display.columns[1:]:
        display[column] = display[column].map(_format_number)
    return display


def _build_cen_projection_evolution(projections: pd.DataFrame) -> pd.DataFrame:
    """Convert the CEN projection matrix into target-month horizon series."""
    if projections.empty:
        return pd.DataFrame()

    rows = []
    target_columns = [column for column in projections.columns if column != "projection_month"]
    for _, row in projections.iterrows():
        projection_month = _parse_month_label(row.get("projection_month"))
        if projection_month is None:
            continue
        for target_column in target_columns:
            target_month = _parse_month_label(target_column)
            if target_month is None:
                continue
            value = pd.to_numeric(row.get(target_column), errors="coerce")
            if pd.isna(value):
                continue
            months_ahead = _month_distance(projection_month, target_month)
            if 0 <= months_ahead <= 12:
                rows.append(
                    {
                        "target_month": target_month,
                        "target_label": _format_month_label(target_month),
                        "projection_month": projection_month,
                        "projection_label": _format_month_label(projection_month),
                        "months_ahead": months_ahead,
                        "cmg": float(value),
                    }
                )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["target_month", "months_ahead"], ascending=[True, False])


def _render_cen_target_month_filter(evolution: pd.DataFrame, actual_mejillones: pd.DataFrame) -> list[str]:
    """Render a capped selector for CEN target months."""
    targets = evolution[["target_month", "target_label"]].drop_duplicates()
    targets = _sort_target_months_for_selector(targets, actual_mejillones)
    options = targets["target_label"].tolist()
    default = options[:1]
    return st.multiselect(
        "Mes objetivo",
        options=options,
        default=default,
        max_selections=3,
        help="Puedes seleccionar hasta tres meses objetivo para comparar la evolucion de sus proyecciones.",
        key="cen_projection_target_months",
    )


def _sort_target_months_for_selector(targets: pd.DataFrame, actual_mejillones: pd.DataFrame) -> pd.DataFrame:
    """Sort target months around the latest real month.

    Desired order:
    - latest available actual month back to January of that same year,
    - remaining future months of that year and later years in chronological order,
    - previous years in reverse chronological order.
    """
    if targets.empty:
        return targets

    anchor_month = _latest_actual_month(actual_mejillones)
    if anchor_month is None:
        return targets.sort_values("target_month", ascending=False)

    targets = targets.copy()
    targets["target_month"] = pd.to_datetime(targets["target_month"])
    month_order = targets["target_month"].dt.year * 12 + targets["target_month"].dt.month
    targets["sort_group"] = 3
    targets["sort_value"] = month_order

    same_year_history = (targets["target_month"].dt.year == anchor_month.year) & (
        targets["target_month"] <= anchor_month
    )
    future_months = targets["target_month"] > anchor_month
    older_months = targets["target_month"] < anchor_month

    targets.loc[same_year_history, "sort_group"] = 0
    targets.loc[same_year_history, "sort_value"] = -month_order[same_year_history]
    targets.loc[future_months, "sort_group"] = 1
    targets.loc[older_months & ~same_year_history, "sort_group"] = 2
    targets.loc[older_months & ~same_year_history, "sort_value"] = -month_order[older_months & ~same_year_history]

    return targets.sort_values(["sort_group", "sort_value"])[["target_month", "target_label"]]


def _latest_actual_month(actual_mejillones: pd.DataFrame) -> pd.Timestamp | None:
    """Return the latest month with actual Mejillones data, even if partial."""
    if actual_mejillones.empty:
        return None

    latest = pd.Timestamp(actual_mejillones["actual_until"].max())
    return latest.to_period("M").to_timestamp()


def _build_mejillones_actual_monthly_average(observations: pd.DataFrame) -> pd.DataFrame:
    """Return actual monthly average for Mejillones 110."""
    actual = observations[observations["node_name"] == "Mejillones 110"].copy()
    if actual.empty:
        return pd.DataFrame(columns=["target_month", "target_label", "actual_cmg", "actual_until"])

    monthly = monthly_average(actual)
    monthly = monthly[monthly["node_name"] == "Mejillones 110"].copy()
    if monthly.empty:
        return pd.DataFrame(columns=["target_month", "target_label", "actual_cmg", "actual_until"])

    actual["month"] = actual["timestamp"].dt.to_period("M").dt.to_timestamp()
    actual_until = actual.groupby("month", as_index=False)["timestamp"].max().rename(columns={"timestamp": "actual_until"})
    monthly = monthly.merge(actual_until, on="month", how="left")
    monthly = monthly.rename(columns={"month": "target_month", "average_cost": "actual_cmg"})
    monthly["target_label"] = monthly["target_month"].map(_format_month_label)
    return monthly[["target_month", "target_label", "actual_cmg", "actual_until"]].sort_values("target_month")


def _cen_projection_evolution_chart(evolution: pd.DataFrame, actual_mejillones: pd.DataFrame) -> go.Figure:
    """Return line chart showing how CEN projections compare with actual prices."""
    fig = go.Figure()
    palette = [
        "#0F4C81",
        "#1B998B",
        "#F46036",
        "#6C63FF",
        "#EDB458",
        "#2D9CDB",
        "#9B51E0",
        "#27AE60",
        "#EB5757",
        "#4F4F4F",
        "#56CCF2",
        "#F2994A",
    ]
    targets = list(evolution["target_label"].drop_duplicates())
    for index, target_label in enumerate(targets):
        target_data = evolution[evolution["target_label"] == target_label].sort_values("months_ahead", ascending=False)
        color = palette[index % len(palette)]
        customdata = target_data[["target_label", "projection_label", "months_ahead", "cmg"]]
        fig.add_trace(
            go.Scatter(
                x=target_data["months_ahead"],
                y=target_data["cmg"],
                name=target_label,
                mode="lines+markers",
                line=dict(color=color, width=1.8),
                marker=dict(size=5, color=color),
                opacity=0.82,
                customdata=customdata,
                hovertemplate=(
                    "Mes objetivo: %{customdata[0]}<br>"
                    "Proyección realizada: %{customdata[1]}<br>"
                    "Meses de anticipación: %{customdata[2]}<br>"
                    "CMg proyectado: %{customdata[3]:.2f} USD/MWh"
                    "<extra></extra>"
                ),
            )
        )

    current_points = evolution[evolution["months_ahead"] == 0].copy()
    if not current_points.empty:
        current_customdata = current_points[["target_label", "projection_label", "months_ahead", "cmg"]]
        fig.add_trace(
            go.Scatter(
                x=current_points["months_ahead"],
                y=current_points["cmg"],
                name="Mes objetivo (0)",
                mode="markers",
                marker=dict(size=10, color="#FFFFFF", line=dict(color="#111827", width=2)),
                customdata=current_customdata,
                hovertemplate=(
                    "Mes objetivo: %{customdata[0]}<br>"
                    "Proyección realizada: %{customdata[1]}<br>"
                    "Meses de anticipación: %{customdata[2]}<br>"
                    "CMg proyectado: %{customdata[3]:.2f} USD/MWh"
                    "<extra>Mes objetivo (0)</extra>"
                ),
            )
        )

    actual_points = _actual_points_for_selected_targets(evolution, actual_mejillones)
    if not actual_points.empty:
        color_by_target = {target_label: palette[index % len(palette)] for index, target_label in enumerate(targets)}
        for _, actual_point in actual_points.iterrows():
            target_label = actual_point["target_label"]
            customdata = [[target_label, actual_point["actual_until"], actual_point["actual_cmg"]]]
            fig.add_trace(
                go.Scatter(
                    x=[0],
                    y=[actual_point["actual_cmg"]],
                    name=f"Real {target_label}",
                    mode="markers",
                    marker=dict(
                        symbol="diamond",
                        size=14,
                        color=color_by_target.get(target_label, "#C00000"),
                        line=dict(color="#111827", width=1.5),
                    ),
                    customdata=customdata,
                    hovertemplate=(
                        "Mes objetivo: %{customdata[0]}<br>"
                        "Precio real promedio Mejillones 110: %{customdata[2]:.2f} USD/MWh<br>"
                        "Data real cargada hasta: %{customdata[1]|%d-%m-%Y %H:%M}"
                        f"<extra>Real Mejillones 110 - {target_label}</extra>"
                    ),
                )
            )

    fig.update_layout(
        template="plotly_white",
        height=430,
        margin=dict(l=10, r=10, t=20, b=80),
        xaxis_title="Meses de anticipación respecto al mes objetivo",
        yaxis_title="CMg (USD/MWh)",
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        legend_title_text="Mes objetivo",
        hovermode="closest",
    )
    fig.update_xaxes(tickmode="array", tickvals=list(range(12, -1, -1)), range=[12.2, -0.2])
    return fig


def _actual_points_for_selected_targets(evolution: pd.DataFrame, actual_mejillones: pd.DataFrame) -> pd.DataFrame:
    """Keep actual Mejillones points only for target months shown in the chart."""
    if evolution.empty or actual_mejillones.empty:
        return pd.DataFrame()

    selected_targets = evolution[["target_month", "target_label"]].drop_duplicates()
    actual_points = selected_targets.merge(actual_mejillones, on=["target_month", "target_label"], how="inner")
    return actual_points.dropna(subset=["actual_cmg"]).sort_values("target_month")


def _monthly_context_caption(daily_context: pd.DataFrame) -> str:
    latest_cmg = _latest_date(daily_context, "monthly_average_cmg")
    latest_coal = _latest_date(daily_context, "coal_price")
    return f"Último CMg mensual: {_format_date(latest_cmg)} | Último precio carbón: {_format_date(latest_coal)}."


def _daily_context_caption(daily_context: pd.DataFrame) -> str:
    latest_daily = _latest_date(daily_context, "daily_cmg")
    latest_projection = _latest_date(daily_context, "cen_monthly_projection")
    return f"Último CMg diario: {_format_date(latest_daily)} | Proyección CEN hasta: {_format_date(latest_projection)}."


def _projection_context_caption(projections: pd.DataFrame) -> str:
    latest_projection = _latest_projection_row(projections)
    if latest_projection is None:
        return "Sin proyecciones CEN disponibles."
    projection_month, _ = latest_projection
    start_month = _projection_window_start(projection_month)
    end_month = start_month + pd.DateOffset(months=5)
    return (
        f"Última proyección disponible: {_format_month_label(projection_month)}. "
        f"Ventana mostrada: {_format_month_label(start_month)} a {_format_month_label(end_month)}."
    )


def _latest_projection_cards(projections: pd.DataFrame) -> list[tuple[str, str, str | None]]:
    latest_projection = _latest_projection_row(projections)
    if latest_projection is None:
        return [("Proyección CEN", "", "USD/MWh")]

    projection_month, row = latest_projection
    start_month = _projection_window_start(projection_month)
    cards = []
    for offset in range(6):
        month = start_month + pd.DateOffset(months=offset)
        column = _format_month_label(month)
        value = row.get(column)
        cards.append((_format_month_title(month), _format_number(value), "USD/MWh"))
    return cards


def _latest_projection_row(projections: pd.DataFrame) -> tuple[pd.Timestamp, pd.Series] | None:
    if projections.empty:
        return None
    parsed = projections["projection_month"].map(_parse_month_label)
    valid = parsed.dropna()
    if valid.empty:
        return None
    latest_index = valid.idxmax()
    return parsed.loc[latest_index], projections.loc[latest_index]


def _projection_window_start(projection_month: pd.Timestamp) -> pd.Timestamp:
    current_month = pd.Timestamp.today().normalize().to_period("M").to_timestamp()
    return max(current_month, projection_month)


def _month_distance(start_month: pd.Timestamp, end_month: pd.Timestamp) -> int:
    start = pd.Timestamp(start_month)
    end = pd.Timestamp(end_month)
    return (end.year - start.year) * 12 + (end.month - start.month)


def _parse_month_label(label: object) -> pd.Timestamp | None:
    if not isinstance(label, str) or "-" not in label:
        return None
    month_label, year_label = label.split("-", 1)
    month = MONTH_NUMBERS.get(month_label.strip().lower())
    if month is None:
        return None
    year = 2000 + int(year_label)
    return pd.Timestamp(year=year, month=month, day=1)


def _format_month_label(month: pd.Timestamp) -> str:
    timestamp = pd.Timestamp(month)
    return f"{MONTH_LABELS[timestamp.month]}-{timestamp.strftime('%y')}"


def _format_month_title(month: pd.Timestamp) -> str:
    timestamp = pd.Timestamp(month)
    return f"{MONTH_LABELS[timestamp.month].capitalize()} {timestamp.year}"


def _latest_date(data: pd.DataFrame, column: str) -> pd.Timestamp | None:
    available = data.dropna(subset=[column])
    if available.empty:
        return None
    return available["date"].max()


def _format_date(value: pd.Timestamp | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%d-%m-%Y")


def _format_number(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
