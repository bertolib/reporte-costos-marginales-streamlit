"""Verified report snapshot for temporary database outages."""

import pandas as pd
import json

from config.settings import PROJECT_ROOT
from src.domain.enums import Granularity
from src.infrastructure.repositories.supabase_market_repository import SupabaseMarketRepository


SNAPSHOT_PATH = PROJECT_ROOT / "database" / "snapshots" / "cmg_verified.csv.gz"


class SnapshotMarketRepository(SupabaseMarketRepository):
    """Reuse the canonical transformations without creating a network client."""

    def __init__(self) -> None:
        self.source_path = SNAPSHOT_PATH

    def _fetch_all_records(self) -> list[dict]:
        return pd.read_csv(self.source_path).to_dict(orient="records")

    def load_observations(self, granularity: Granularity) -> pd.DataFrame:
        data = super().load_observations(granularity)
        metadata = json.loads(self.source_path.with_name("metadata.json").read_text(encoding="utf-8"))
        data.attrs["data_loaded_at"] = pd.Timestamp(metadata["data_loaded_date_local"])
        return data

    def get_last_update(self) -> pd.Timestamp | None:
        timestamps = pd.read_csv(self.source_path, usecols=["timestamp"])["timestamp"]
        return pd.to_datetime(timestamps).max() if not timestamps.empty else None
