from pathlib import Path

import pandas as pd

from config.settings import DEFAULT_EXCEL_PATH
from src.domain.enums import Granularity
from src.infrastructure.repositories.excel_market_repository import ExcelMarketRepository
from src.presentation.pages.marginal_costs import _build_cen_projection_evolution


def test_hourly_repository_returns_canonical_columns() -> None:
    repository = ExcelMarketRepository(Path(DEFAULT_EXCEL_PATH))
    observations = repository.load_observations(Granularity.HOURLY)

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
    assert observations["node_name"].nunique() >= 4
    assert observations["value"].notna().all()


def test_fifteen_minute_repository_handles_midnight_hours() -> None:
    repository = ExcelMarketRepository(Path(DEFAULT_EXCEL_PATH))
    observations = repository.load_observations(Granularity.FIFTEEN_MINUTES)

    mejillones = observations[observations["node_name"] == "Mejillones 110"]
    window = mejillones[
        (mejillones["timestamp"] >= "2026-07-30 23:00")
        & (mejillones["timestamp"] <= "2026-07-31 01:00")
    ]

    expected_timestamps = [
        "2026-07-30 23:00",
        "2026-07-30 23:15",
        "2026-07-30 23:30",
        "2026-07-30 23:45",
        "2026-07-31 00:00",
        "2026-07-31 00:15",
        "2026-07-31 00:30",
        "2026-07-31 00:45",
        "2026-07-31 01:00",
    ]
    actual_timestamps = window["timestamp"].dt.strftime("%Y-%m-%d %H:%M").tolist()

    assert actual_timestamps == expected_timestamps
    assert not window["timestamp"].duplicated().any()


def test_cen_projection_evolution_aligns_target_horizon() -> None:
    projections = pd.DataFrame(
        [
            {"projection_month": "jun-26", "jul-26": 85.83, "dic-26": 34.52, "jun-26": 132.22},
            {"projection_month": "jul-26", "dic-26": 35.10, "jul-26": 80.00},
        ]
    )

    evolution = _build_cen_projection_evolution(projections)
    dic_from_jun = evolution[
        (evolution["target_label"] == "dic-26")
        & (evolution["projection_label"] == "jun-26")
    ].iloc[0]
    jul_target = evolution[
        (evolution["target_label"] == "jul-26")
        & (evolution["projection_label"] == "jul-26")
    ].iloc[0]

    assert dic_from_jun["months_ahead"] == 6
    assert dic_from_jun["cmg"] == 34.52
    assert jul_target["months_ahead"] == 0
