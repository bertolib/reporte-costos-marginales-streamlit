"""Plotly chart builders."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.analytics.aggregations import daily_average, daily_bess_arbitrage, heatmap_matrix, hourly_profile, monthly_average


PLOTLY_TEMPLATE = "plotly_white"


def _compact_legend(show: bool = True) -> dict:
    return dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0) if show else {}


def _date_tick_values(dates: pd.Series, max_ticks: int = 7) -> list[pd.Timestamp]:
    """Return readable date ticks, always keeping the final day visible."""
    clean_dates = pd.Series(pd.to_datetime(dates).dt.normalize().dropna().unique()).sort_values()
    if clean_dates.empty:
        return []

    start = pd.Timestamp(clean_dates.iloc[0])
    end = pd.Timestamp(clean_dates.iloc[-1])
    if start == end:
        return [start]

    total_days = max((end - start).days, 1)
    step_days = max(round(total_days / max(max_ticks - 1, 1)), 1)
    ticks = list(pd.date_range(start=start, end=end, freq=f"{step_days}D"))
    if ticks[-1] != end:
        ticks.append(end)
    return ticks


def daily_trend_chart(observations: pd.DataFrame) -> go.Figure:
    data = daily_average(observations)
    fig = px.line(
        data,
        x="date",
        y="average_cost",
        color="node_name",
        labels={"date": "Fecha", "average_cost": "USD/MWh", "node_name": "Barra"},
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(
        legend_title_text="",
        legend=_compact_legend(),
        margin=dict(l=10, r=10, t=20, b=10),
        height=380,
    )
    tick_values = _date_tick_values(data["date"]) if not data.empty else []
    fig.update_xaxes(
        tickformat="%d-%m-%y",
        hoverformat="%d-%m-%Y",
        tickmode="array",
        tickvals=tick_values,
        range=[tick_values[0], tick_values[-1]] if tick_values else None,
    )
    return fig


def monthly_chart(observations: pd.DataFrame) -> go.Figure:
    data = monthly_average(observations)
    fig = px.bar(
        data,
        x="month",
        y="average_cost",
        color="node_name",
        barmode="group",
        labels={"month": "Mes", "average_cost": "USD/MWh", "node_name": "Barra"},
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(
        legend_title_text="",
        legend=_compact_legend(),
        margin=dict(l=10, r=10, t=20, b=10),
        height=340,
    )
    return fig


def last_six_months_average_chart(observations: pd.DataFrame, period_end: pd.Timestamp | None = None) -> go.Figure:
    """Return monthly average chart for the six-month window ending in the selected period."""
    data = monthly_average(observations)
    if period_end is not None and not data.empty:
        end_month = pd.Timestamp(period_end).to_period("M").to_timestamp()
        first_month = end_month - pd.DateOffset(months=5)
        data = data[(data["month"] >= first_month) & (data["month"] <= end_month)]

    fig = px.bar(
        data,
        x="month",
        y="average_cost",
        color="node_name",
        barmode="group",
        text="average_cost",
        labels={"month": "Mes", "average_cost": "USD/MWh", "node_name": "Barra"},
        template=PLOTLY_TEMPLATE,
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
    show_legend = data["node_name"].nunique() > 1 if not data.empty else False
    fig.update_layout(
        barmode="group",
        legend_title_text="",
        showlegend=show_legend,
        legend=_compact_legend(show_legend),
        margin=dict(l=10, r=10, t=20, b=10),
        height=360,
    )
    return fig


def hourly_profile_chart(observations: pd.DataFrame) -> go.Figure:
    data = hourly_profile(observations)
    fig = px.line(
        data,
        x="hour",
        y="average_cost",
        color="node_name",
        markers=True,
        labels={"hour": "Hora", "average_cost": "USD/MWh", "node_name": "Barra"},
        template=PLOTLY_TEMPLATE,
    )
    show_legend = data["node_name"].nunique() > 1 if not data.empty else False
    fig.update_xaxes(tickmode="array", tickvals=[1, 4, 7, 10, 13, 16, 19, 22, 24], tickangle=0)
    fig.update_layout(
        legend_title_text="",
        showlegend=show_legend,
        legend=_compact_legend(show_legend),
        margin=dict(l=10, r=10, t=20, b=10),
        height=340,
    )
    return fig


def daily_cmg_history_chart(daily_context: pd.DataFrame) -> go.Figure:
    """Return daily CMg history from the CMg Diario worksheet."""
    data = daily_context[daily_context["date"] >= pd.Timestamp("2023-01-01")].copy()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["daily_cmg"],
            name="Cmg Diario",
            mode="lines",
            line=dict(color="#4472C4", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["monthly_average_cmg"],
            name="Cmg promedio Mensual",
            mode="lines",
            line=dict(color="#ED7D31", width=2),
        )
    )
    projected = data.dropna(subset=["cen_monthly_projection"])
    if not projected.empty:
        fig.add_trace(
            go.Scatter(
                x=projected["date"],
                y=projected["cen_monthly_projection"],
                name="Programado Cen Mensual",
                mode="lines",
                line=dict(color="#A6A6A6", width=2, dash="dash"),
            )
        )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        legend_title_text="",
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=20, b=70),
        height=430,
        yaxis_title="USD/MWh",
        xaxis_title="",
    )
    return fig


def monthly_cmg_coal_chart(daily_context: pd.DataFrame) -> go.Figure:
    """Return monthly historical CMg and coal price from the CMg Diario worksheet."""
    data = daily_context[daily_context["date"] >= pd.Timestamp("2013-01-01")].copy()
    data = data.dropna(subset=["monthly_average_cmg"])
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["coal_price"],
            name="Precio Carbon",
            mode="lines",
            line=dict(color="#FFC000", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data["date"],
            y=data["monthly_average_cmg"],
            name="Cmg promedio Mensual",
            mode="lines",
            line=dict(color="#C00000", width=2, shape="hv"),
        )
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        legend_title_text="",
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5),
        margin=dict(l=10, r=10, t=20, b=70),
        height=430,
        yaxis_title="USD/MWh",
        xaxis_title="",
    )
    return fig


def bess_arbitrage_chart(observations: pd.DataFrame) -> go.Figure:
    """Return daily gross BESS arbitrage spread chart."""
    data = daily_bess_arbitrage(observations)
    fig = go.Figure()
    if data.empty:
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            margin=dict(l=10, r=10, t=20, b=10),
            height=360,
            annotations=[
                dict(
                    text="Sin datos para el periodo seleccionado",
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(color="#667085"),
                )
            ],
        )
        return fig

    palette = px.colors.qualitative.Safe
    nodes = list(data["node_name"].drop_duplicates())
    average_spread = data["spread"].mean()
    for index, node_name in enumerate(nodes):
        node_data = data[data["node_name"] == node_name]
        color = palette[index % len(palette)]
        customdata = node_data[["min_cost", "min_hour", "max_cost", "max_hour", "spread"]]
        fig.add_trace(
            go.Bar(
                x=node_data["date"],
                y=node_data["spread"],
                name=node_name,
                marker_color=color,
                customdata=customdata,
                hovertemplate=(
                    "Fecha: %{x|%d-%m-%Y}<br>"
                    "CMg minimo: %{customdata[0]:.2f} USD/MWh<br>"
                    "Hora minima: %{customdata[1]:.0f}<br>"
                    "CMg maximo: %{customdata[2]:.2f} USD/MWh<br>"
                    "Hora maxima: %{customdata[3]:.0f}<br>"
                    "Spread diario: %{customdata[4]:.2f} USD/MWh"
                    "<extra>%{fullData.name}</extra>"
                ),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=node_data["date"],
                y=node_data["rolling_7d_spread"],
                name=f"PM 7d - {node_name}",
                mode="lines",
                line=dict(color=color, width=2),
                hovertemplate=(
                    "Fecha: %{x|%d-%m-%Y}<br>"
                    "Prom. mov. 7d: %{y:.2f} USD/MWh"
                    "<extra>%{fullData.name}</extra>"
                ),
            )
        )

    fig.add_hline(
        y=average_spread,
        line_dash="dash",
        line_color="#1F2937",
        annotation_text=f"Promedio periodo: {average_spread:.1f} USD/MWh",
        annotation_position="top left",
    )
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        barmode="group",
        legend_title_text="",
        legend=_compact_legend(),
        margin=dict(l=10, r=10, t=20, b=10),
        height=370,
        yaxis_title="Spread bruto diario (USD/MWh)",
        xaxis_title="Fecha",
    )
    return fig


def node_heatmap(observations: pd.DataFrame, node_name: str) -> go.Figure:
    matrix = heatmap_matrix(observations, node_name)
    fig = px.imshow(
        matrix,
        aspect="auto",
        color_continuous_scale="RdYlBu_r",
        labels={"x": "Fecha", "y": "Hora", "color": "USD/MWh"},
        template=PLOTLY_TEMPLATE,
    )
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=520)
    return fig
