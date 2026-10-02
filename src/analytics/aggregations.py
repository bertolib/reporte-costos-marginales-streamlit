"""Reusable aggregations for marginal-cost observations."""

import pandas as pd


def filter_period(
    observations: pd.DataFrame,
    start_date: pd.Timestamp | None,
    end_date: pd.Timestamp | None,
    nodes: list[str] | None = None,
    zones: list[str] | None = None,
    scenarios: list[str] | None = None,
) -> pd.DataFrame:
    """Filter observations by date range, node and zone."""
    df = observations.copy()
    if start_date is not None:
        df = df[df["timestamp"] >= pd.Timestamp(start_date)]
    if end_date is not None:
        df = df[df["timestamp"] <= pd.Timestamp(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)]
    if nodes:
        df = df[df["node_name"].isin(nodes)]
    if zones:
        df = df[df["zone"].isin(zones)]
    if scenarios:
        df = df[df["scenario"].isin(scenarios)]
    return df


def monthly_average(observations: pd.DataFrame) -> pd.DataFrame:
    """Return monthly average marginal cost by node."""
    df = observations.copy()
    df["month"] = df["timestamp"].dt.to_period("M").dt.to_timestamp()
    return (
        df.groupby(["month", "node_name", "zone"], as_index=False)["value"]
        .mean()
        .rename(columns={"value": "average_cost"})
        .sort_values(["month", "node_name"])
    )


def daily_average(observations: pd.DataFrame) -> pd.DataFrame:
    """Return daily average marginal cost by node."""
    df = observations.copy()
    df["date"] = df["timestamp"].dt.date
    return (
        df.groupby(["date", "node_name", "zone"], as_index=False)["value"]
        .mean()
        .rename(columns={"value": "average_cost"})
        .sort_values(["date", "node_name"])
    )


def hourly_profile(observations: pd.DataFrame) -> pd.DataFrame:
    """Return average cost by hour and node."""
    df = observations.copy()
    df["hour"] = df["timestamp"].dt.hour + 1
    return (
        df.groupby(["hour", "node_name", "zone"], as_index=False)["value"]
        .mean()
        .rename(columns={"value": "average_cost"})
        .sort_values(["hour", "node_name"])
    )


def daily_bess_arbitrage(observations: pd.DataFrame) -> pd.DataFrame:
    """Return daily min/max hourly spread by node for BESS arbitrage screening."""
    if observations.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "node_name",
                "zone",
                "min_cost",
                "min_hour",
                "max_cost",
                "max_hour",
                "spread",
                "rolling_7d_spread",
            ]
        )

    df = observations.copy()
    df["date"] = df["timestamp"].dt.normalize()
    df["hour"] = df["timestamp"].dt.hour + 1
    df = df.dropna(subset=["date", "node_name", "zone", "value"])
    if df.empty:
        return pd.DataFrame()

    group_cols = ["date", "node_name", "zone"]
    min_rows = df.loc[df.groupby(group_cols)["value"].idxmin(), [*group_cols, "value", "hour"]]
    max_rows = df.loc[df.groupby(group_cols)["value"].idxmax(), [*group_cols, "value", "hour"]]
    min_rows = min_rows.rename(columns={"value": "min_cost", "hour": "min_hour"})
    max_rows = max_rows.rename(columns={"value": "max_cost", "hour": "max_hour"})

    arbitrage = min_rows.merge(max_rows, on=group_cols, how="inner")
    arbitrage["spread"] = arbitrage["max_cost"] - arbitrage["min_cost"]
    arbitrage = arbitrage.sort_values(["node_name", "date"])
    arbitrage["rolling_7d_spread"] = arbitrage.groupby("node_name")["spread"].transform(
        lambda series: series.rolling(window=7, min_periods=1).mean()
    )
    return arbitrage.sort_values(["date", "node_name"])


def heatmap_matrix(observations: pd.DataFrame, node_name: str) -> pd.DataFrame:
    """Build hour by date matrix for heatmap visualization."""
    df = observations[observations["node_name"] == node_name].copy()
    df["date"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.hour + 1
    pivot = df.pivot_table(
        index="hour",
        columns="date",
        values="value",
        aggfunc="mean",
    )
    return pivot.sort_index()
