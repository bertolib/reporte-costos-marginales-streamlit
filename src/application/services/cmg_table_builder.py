"""Build Excel-shaped marginal-cost tables from canonical observations."""

from datetime import time

import pandas as pd

from src.domain.enums import Granularity
from src.infrastructure.repositories.tsv_market_repository import TsvMarketRepository


EXCEL_COST_COLUMNS = [
    "Cmg Mej 110 (USD/MWh)",
    "Cmg Chaca 110 (CLP)",
    "Cmg Chacaya 110 (USD/MWh)",
    "Alto Jahuel 220 (USD/MWh)",
    "Charrua 220 (USD/MWh)",
]

NODE_TO_EXCEL_COLUMN = {
    "cmg_mej_110": "Cmg Mej 110 (USD/MWh)",
    "cmg_chaca_110_clp": "Cmg Chaca 110 (CLP)",
    "cmg_chacaya_110": "Cmg Chacaya 110 (USD/MWh)",
    "alto_jahuel_220": "Alto Jahuel 220 (USD/MWh)",
    "charrua_220": "Charrua 220 (USD/MWh)",
}


def build_excel_15min_table(repository: TsvMarketRepository) -> pd.DataFrame:
    """Return the native 15-minute table using the workbook's layout."""
    observations = repository.load_observations(Granularity.FIFTEEN_MINUTES)
    if observations.empty:
        return _empty_15min_table()

    wide = _pivot_observations(observations)
    minute = wide["timestamp"].dt.minute
    hour = wide["timestamp"].dt.hour
    excel_hour = hour.where(minute.ne(0), hour + 1)
    excel_idx = hour + 1

    wide.insert(0, "idx", excel_idx.astype(float))
    wide.insert(1, "Mes", wide["timestamp"].dt.month)
    wide.insert(2, "Fecha", wide["timestamp"].dt.normalize())
    wide.insert(3, "Anio", wide["timestamp"].dt.year)
    wide.insert(4, "Hora", excel_hour.astype(int))
    wide.insert(5, "Minutos", minute.map(lambda value: time(0, int(value))))
    return wide[
        [
            "idx",
            "Mes",
            "Fecha",
            "Anio",
            "Hora",
            "Minutos",
            *EXCEL_COST_COLUMNS,
        ]
    ].sort_values(["Fecha", "idx", "Minutos"], key=_sort_15min_key)


def build_supabase_15min_table(repository: TsvMarketRepository) -> pd.DataFrame:
    """Return the 15-minute report table ready for Supabase loading."""
    observations = repository.load_observations(Granularity.FIFTEEN_MINUTES)
    if observations.empty:
        return pd.DataFrame(
            columns=[
                "fecha",
                "hora",
                "minutos",
                "timestamp",
                "cmg_mej_110_usd_mwh",
                "cmg_chaca_110_clp_kwh",
                "cmg_chacaya_110_usd_mwh",
                "alto_jahuel_220_usd_mwh",
                "charrua_220_usd_mwh",
                "source_file",
                "version",
            ]
        )

    wide = _pivot_observations(observations)
    source_by_timestamp = (
        observations.groupby("timestamp", as_index=False)["source"]
        .first()
        .rename(columns={"source": "source_file"})
    )
    wide = wide.merge(source_by_timestamp, on="timestamp", how="left")
    wide["fecha"] = wide["timestamp"].dt.date
    wide["hora"] = wide["timestamp"].dt.hour.astype(int)
    wide["minutos"] = wide["timestamp"].dt.minute.astype(int)
    wide["version"] = wide["source_file"].map(_extract_version_from_source)
    wide = wide.rename(
        columns={
            "Cmg Mej 110 (USD/MWh)": "cmg_mej_110_usd_mwh",
            "Cmg Chaca 110 (CLP)": "cmg_chaca_110_clp_kwh",
            "Cmg Chacaya 110 (USD/MWh)": "cmg_chacaya_110_usd_mwh",
            "Alto Jahuel 220 (USD/MWh)": "alto_jahuel_220_usd_mwh",
            "Charrua 220 (USD/MWh)": "charrua_220_usd_mwh",
        }
    )
    return wide[
        [
            "fecha",
            "hora",
            "minutos",
            "timestamp",
            "cmg_mej_110_usd_mwh",
            "cmg_chaca_110_clp_kwh",
            "cmg_chacaya_110_usd_mwh",
            "alto_jahuel_220_usd_mwh",
            "charrua_220_usd_mwh",
            "source_file",
            "version",
        ]
    ].sort_values("timestamp")


def build_excel_hourly_table(repository: TsvMarketRepository) -> pd.DataFrame:
    """Return the hourly table derived as the average of four 15-minute rows."""
    observations = repository.load_observations(Granularity.HOURLY)
    if observations.empty:
        return _empty_hourly_table()

    wide = _pivot_observations(observations)
    wide.insert(0, "Hora", wide["timestamp"].dt.hour + 1)
    wide.insert(1, "Anio", wide["timestamp"].dt.year)
    wide.insert(2, "Fecha", wide["timestamp"].dt.normalize())
    wide["Vacio"] = pd.NA
    return wide[
        [
            "Hora",
            "Anio",
            "Fecha",
            *EXCEL_COST_COLUMNS,
            "Vacio",
        ]
    ].sort_values(["Fecha", "Hora"])


def _pivot_observations(observations: pd.DataFrame) -> pd.DataFrame:
    wide = observations.copy()
    wide["excel_column"] = wide["node_id"].map(NODE_TO_EXCEL_COLUMN)
    wide = wide.pivot_table(
        index="timestamp",
        columns="excel_column",
        values="value",
        aggfunc="mean",
    ).reset_index()
    wide.columns.name = None
    for column in EXCEL_COST_COLUMNS:
        if column not in wide.columns:
            wide[column] = pd.NA
    return wide[["timestamp", *EXCEL_COST_COLUMNS]]


def _sort_15min_key(series: pd.Series) -> pd.Series:
    if series.name != "Minutos":
        return series
    minutes = series.map(lambda value: value.hour * 60 + value.minute)
    return minutes.replace(0, 60)


def _extract_version_from_source(source_file: str) -> str | None:
    if not isinstance(source_file, str):
        return None
    stem = source_file.rsplit(".", 1)[0]
    parts = stem.split("_", maxsplit=2)
    if len(parts) < 3:
        return None
    return parts[2]


def _empty_15min_table() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "idx",
            "Mes",
            "Fecha",
            "Anio",
            "Hora",
            "Minutos",
            *EXCEL_COST_COLUMNS,
        ]
    )


def _empty_hourly_table() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "Hora",
            "Anio",
            "Fecha",
            *EXCEL_COST_COLUMNS,
            "Vacio",
        ]
    )
