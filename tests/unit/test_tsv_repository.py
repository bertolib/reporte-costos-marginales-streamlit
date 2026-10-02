from pathlib import Path

import pandas as pd
import pytest

from src.domain.enums import Granularity
from src.infrastructure.repositories.tsv_market_repository import TsvMarketRepository


DATA_DIR = Path("data")
ACTIVE_TSV = next(DATA_DIR.glob("*.tsv"))


def test_tsv_repository_returns_selected_fifteen_minute_series() -> None:
    repository = TsvMarketRepository(DATA_DIR)
    source = pd.read_csv(ACTIVE_TSV, sep="\t", usecols=["FECHA"])

    observations = repository.load_observations(Granularity.FIFTEEN_MINUTES)

    assert not observations.empty
    assert list(observations.columns) == [
        "timestamp",
        "node_id",
        "node_name",
        "zone",
        "value",
        "unit",
        "granularity",
        "scenario",
        "source",
    ]
    assert set(observations["node_id"]) == {
        "cmg_mej_110",
        "cmg_chaca_110_clp",
        "cmg_chacaya_110",
        "alto_jahuel_220",
        "charrua_220",
    }
    source_dates = pd.to_datetime(source["FECHA"])
    assert observations["timestamp"].min() == source_dates.min()
    assert observations["timestamp"].max() == source_dates.max() + pd.Timedelta(hours=23, minutes=45)


def test_tsv_hourly_average_matches_current_excel_workbook() -> None:
    repository = TsvMarketRepository(DATA_DIR)

    observations = repository.load_observations(Granularity.HOURLY)
    first_hour = observations[
        (observations["timestamp"] == observations["timestamp"].min())
        & (observations["node_id"] == "cmg_chacaya_110")
    ].iloc[0]

    native = pd.read_csv(ACTIVE_TSV, sep="\t")
    first_date = native["FECHA"].min()
    expected = native[
        (native["FECHA"] == first_date)
        & (native["HRA"] == 0)
        & (native["BARRA_TRANSF"] == "CHACAYA_______110")
    ]["CMg[USD/MWh]"].mean()
    assert first_hour["value"] == pytest.approx(expected)
    assert first_hour["unit"] == "USD/MWh"


def test_tsv_chaca_clp_series_matches_excel_column_semantics() -> None:
    repository = TsvMarketRepository(DATA_DIR)

    observations = repository.load_observations(Granularity.HOURLY)
    first_hour = observations[
        (observations["timestamp"] == observations["timestamp"].min())
        & (observations["node_id"] == "cmg_chaca_110_clp")
    ].iloc[0]

    native = pd.read_csv(ACTIVE_TSV, sep="\t")
    first_date = native["FECHA"].min()
    expected = native[
        (native["FECHA"] == first_date)
        & (native["HRA"] == 0)
        & (native["BARRA_TRANSF"] == "CHACAYA_______110")
    ]["CMg[CLP/KWh]"].mean()
    assert first_hour["value"] == pytest.approx(expected)
    assert first_hour["unit"] == "CLP/KWh"
