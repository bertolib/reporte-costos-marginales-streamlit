from pathlib import Path

import pandas as pd
import pytest

from src.application.services.cmg_table_builder import (
    build_excel_15min_table,
    build_excel_hourly_table,
    build_supabase_15min_table,
)
from src.infrastructure.repositories.tsv_market_repository import TsvMarketRepository


DATA_DIR = Path("data")
ACTIVE_TSV = next(DATA_DIR.glob("*.tsv"))


def test_build_excel_15min_table_matches_workbook_row_convention() -> None:
    repository = TsvMarketRepository(DATA_DIR)

    table = build_excel_15min_table(repository)
    first_day = table[table["Fecha"] == table["Fecha"].min()].head(4)

    assert first_day["Hora"].tolist() == [0, 0, 0, 1]
    assert [value.strftime("%H:%M:%S") for value in first_day["Minutos"]] == [
        "00:15:00",
        "00:30:00",
        "00:45:00",
        "00:00:00",
    ]


def test_build_excel_15min_table_uses_native_selected_values() -> None:
    repository = TsvMarketRepository(DATA_DIR)
    native = pd.read_csv(ACTIVE_TSV, sep="\t")
    first_date = native["FECHA"].min()
    expected = native[
        (native["FECHA"] == first_date)
        & (native["HRA"] == 0)
        & (native["MIN"] == 15)
        & (native["BARRA_TRANSF"] == "CHACAYA_______110")
    ].iloc[0]

    table = build_excel_15min_table(repository)
    first_row = table.iloc[0]

    assert first_row["Cmg Chacaya 110 (USD/MWh)"] == pytest.approx(expected["CMg[USD/MWh]"])
    assert first_row["Cmg Chaca 110 (CLP)"] == pytest.approx(expected["CMg[CLP/KWh]"])


def test_build_excel_hourly_table_averages_four_native_records() -> None:
    repository = TsvMarketRepository(DATA_DIR)
    native = pd.read_csv(ACTIVE_TSV, sep="\t")
    first_date = native["FECHA"].min()
    expected = native[
        (native["FECHA"] == first_date)
        & (native["HRA"] == 0)
        & (native["BARRA_TRANSF"] == "CHACAYA_______110")
    ]["CMg[USD/MWh]"].mean()

    table = build_excel_hourly_table(repository)
    first_row = table.iloc[0]

    assert first_row["Hora"] == 1
    assert first_row["Cmg Chacaya 110 (USD/MWh)"] == pytest.approx(expected)


def test_build_supabase_15min_table_keeps_native_hra_min_values() -> None:
    repository = TsvMarketRepository(DATA_DIR)
    native = pd.read_csv(ACTIVE_TSV, sep="\t")
    first_date = native["FECHA"].min()
    expected = native[
        (native["FECHA"] == first_date)
        & (native["HRA"] == 0)
        & (native["MIN"] == 0)
        & (native["BARRA_TRANSF"] == "MEJILLONES____110")
    ].iloc[0]

    table = build_supabase_15min_table(repository)
    first_row = table.iloc[0]

    assert first_row["hora"] == 0
    assert first_row["minutos"] == 0
    assert first_row["cmg_mej_110_usd_mwh"] == pytest.approx(expected["CMg[USD/MWh]"])
