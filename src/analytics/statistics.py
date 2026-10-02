"""Statistical summaries for marginal-cost data."""

import pandas as pd


def describe_costs(observations: pd.DataFrame) -> pd.DataFrame:
    """Return executive statistical summary by node."""
    grouped = observations.groupby("node_name")["value"]
    summary = grouped.agg(
        promedio="mean",
        mediana="median",
        minimo="min",
        maximo="max",
        desviacion="std",
        observaciones="count",
    )
    summary["p10"] = grouped.quantile(0.10)
    summary["p90"] = grouped.quantile(0.90)
    return summary.reset_index().round(2)


def detect_iqr_outliers(observations: pd.DataFrame) -> pd.DataFrame:
    """Detect outliers using the IQR rule by node."""
    frames = []
    for node_name, group in observations.groupby("node_name"):
        q1 = group["value"].quantile(0.25)
        q3 = group["value"].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers = group[(group["value"] < lower) | (group["value"] > upper)].copy()
        outliers["threshold_low"] = lower
        outliers["threshold_high"] = upper
        outliers["node_name"] = node_name
        frames.append(outliers)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
