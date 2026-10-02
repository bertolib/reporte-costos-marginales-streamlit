"""Repository contracts for market data."""

from pathlib import Path
from typing import Protocol

import pandas as pd

from src.domain.enums import Granularity


class MarketRepository(Protocol):
    """Port for reading market observations from any persistence backend."""

    source_path: Path

    def load_observations(self, granularity: Granularity) -> pd.DataFrame:
        """Return observations in canonical long format."""
        ...

    def get_last_update(self) -> pd.Timestamp | None:
        """Return the latest observed timestamp available in the source."""
        ...
