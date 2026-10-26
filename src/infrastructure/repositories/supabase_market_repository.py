"""Supabase-backed market data repository."""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

from config.settings import PROJECT_ROOT, SUPABASE_TABLE, get_setting
from src.domain.enums import Granularity, Scenario
from src.domain.node_catalog import NODE_CATALOG
from src.infrastructure.repositories.market_repository import MarketRepository


SUPABASE_SERIES_COLUMNS = {
    "cmg_mej_110_usd_mwh": ("cmg_mej_110", "USD/MWh"),
    "cmg_chaca_110_clp_kwh": ("cmg_chaca_110_clp", "CLP/KWh"),
    "cmg_chacaya_110_usd_mwh": ("cmg_chacaya_110", "USD/MWh"),
    "alto_jahuel_220_usd_mwh": ("alto_jahuel_220", "USD/MWh"),
    "charrua_220_usd_mwh": ("charrua_220", "USD/MWh"),
}


class SupabaseMarketRepository(MarketRepository):
    """Read marginal-cost observations from Supabase."""

    source_path = Path("supabase")

    def __init__(self, table_name: str = SUPABASE_TABLE, page_size: int = 1_000) -> None:
        load_dotenv(PROJECT_ROOT / ".env")
        supabase_url = get_setting("SUPABASE_URL")
        supabase_key = (
            get_setting("SUPABASE_SECRET_KEY")
            or get_setting("SUPABASE_SERVICE_ROLE_KEY")
            or get_setting("SUPABASE_PUBLISHABLE_KEY")
        )
        if not supabase_url or not supabase_key:
            msg = "Missing SUPABASE_URL and Supabase key in environment or .env"
            raise RuntimeError(msg)
        self.table_name = table_name
        self.page_size = page_size
        self.client = create_client(supabase_url, supabase_key)

    def load_observations(self, granularity: Granularity) -> pd.DataFrame:
        """Return observations in canonical long format."""
        if granularity not in {Granularity.FIFTEEN_MINUTES, Granularity.HOURLY}:
            msg = f"Unsupported Supabase granularity: {granularity}"
            raise ValueError(msg)

        return self._load_fifteen_minutes(granularity)

    def get_last_update(self) -> pd.Timestamp | None:
        """Return latest timestamp available in Supabase."""
        response = (
            self.client.table(self.table_name)
            .select("timestamp")
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return pd.to_datetime(response.data[0]["timestamp"], errors="coerce")

    def _load_fifteen_minutes(
        self, granularity: Granularity = Granularity.FIFTEEN_MINUTES
    ) -> pd.DataFrame:
        records = self._fetch_all_records()
        if not records:
            return self._empty_observations()

        wide = pd.DataFrame(records)
        wide["timestamp"] = pd.to_datetime(wide["timestamp"], errors="coerce")
        # Aggregate before expanding the five series to avoid holding the full
        # 15-minute long table in memory when opening the hourly dashboard.
        if granularity == Granularity.HOURLY:
            wide["timestamp"] = wide["timestamp"].dt.floor("h")
            value_columns = [column for column in SUPABASE_SERIES_COLUMNS if column in wide]
            wide[value_columns] = wide[value_columns].apply(pd.to_numeric, errors="coerce")
            wide = wide.groupby(["timestamp", "source_file"], as_index=False)[value_columns].mean()
        frames = []
        for source_column, (node_id, unit) in SUPABASE_SERIES_COLUMNS.items():
            if source_column not in wide.columns:
                continue
            node = NODE_CATALOG[node_id]
            frame = pd.DataFrame(
                {
                    "timestamp": wide["timestamp"],
                    "node_id": node_id,
                    "node_name": node.name,
                    "zone": node.zone,
                    "value": pd.to_numeric(wide[source_column], errors="coerce"),
                    "unit": unit,
                    "granularity": granularity.value,
                    "scenario": Scenario.ACTUAL.value,
                    "source": wide.get("source_file", "supabase"),
                }
            )
            frames.append(frame.dropna(subset=["timestamp", "value"]))

        if not frames:
            return self._empty_observations()
        return pd.concat(frames, ignore_index=True).sort_values(["timestamp", "node_name", "unit"])

    def _fetch_all_records(self) -> list[dict[str, Any]]:
        columns = [
            "timestamp",
            "source_file",
            *SUPABASE_SERIES_COLUMNS.keys(),
        ]
        def fetch_page(start: int, *, count: bool = False):
            end = start + self.page_size - 1
            return (
                self.client.table(self.table_name)
                .select(",".join(columns), **({"count": "exact"} if count else {}))
                .order("timestamp")
                .range(start, end)
                .execute()
            )

        first = fetch_page(0, count=True)
        records = first.data or []
        total = first.count
        if total is None:
            raise RuntimeError("Supabase did not return the historical record count")
        if len(records) < min(total, self.page_size):
            raise RuntimeError("Supabase returned an incomplete historical page")
        # Bound concurrency so a cold cache does not require dozens of serial
        # network round trips. map preserves timestamp page order.
        with ThreadPoolExecutor(max_workers=4) as executor:
            for response in executor.map(fetch_page, range(self.page_size, total, self.page_size)):
                records.extend(response.data or [])
        if len(records) != total:
            raise RuntimeError("Supabase historical download is incomplete; please retry")
        return records

    @staticmethod
    def _to_hourly(observations: pd.DataFrame) -> pd.DataFrame:
        if observations.empty:
            return observations
        hourly = observations.copy()
        hourly["timestamp"] = hourly["timestamp"].dt.floor("h")
        hourly = (
            hourly.groupby(
                [
                    "timestamp",
                    "node_id",
                    "node_name",
                    "zone",
                    "unit",
                    "scenario",
                    "source",
                ],
                as_index=False,
            )["value"]
            .mean()
            .sort_values(["timestamp", "node_name", "unit"])
        )
        hourly["granularity"] = Granularity.HOURLY.value
        return hourly[
            [
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
        ]

    @staticmethod
    def _empty_observations() -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
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
        )
