"""Verified report snapshot for temporary database outages."""

import pandas as pd

from config.settings import PROJECT_ROOT
from src.infrastructure.repositories.supabase_market_repository import SupabaseMarketRepository


SNAPSHOT_PATH = PROJECT_ROOT / "database" / "snapshots" / "cmg_verified.csv.gz"


class SnapshotMarketRepository(SupabaseMarketRepository):
    """Reuse the canonical transformations without creating a network client."""

    def __init__(self) -> None:
        self.source_path = SNAPSHOT_PATH

    def _fetch_all_records(self) -> list[dict]:
        return pd.read_csv(self.source_path).to_dict(orient="records")

    def get_last_update(self) -> pd.Timestamp | None:
        timestamps = pd.read_csv(self.source_path, usecols=["timestamp"])["timestamp"]
        return pd.to_datetime(timestamps).max() if not timestamps.empty else None
