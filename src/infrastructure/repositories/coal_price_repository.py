"""Verified Newcastle coal closes, independent from the Excel context tables."""

import hashlib
import json
from pathlib import Path

import pandas as pd

from src.infrastructure.repositories.market_context_repository import CONTEXT_DIR


COAL_PATH = CONTEXT_DIR / "coal_prices.csv.gz"
COAL_METADATA = CONTEXT_DIR / "coal_metadata.json"
COAL_SOURCE = "https://www.investing.com/commodities/newcastle-coal-futures-historical-data"


class CoalPriceRepository:
    def __init__(self, path: Path = COAL_PATH, metadata_path: Path = COAL_METADATA):
        self.path = path
        self.metadata_path = metadata_path

    def cache_token(self) -> str:
        if not self.path.exists() and not self.metadata_path.exists():
            return "coal:missing"
        return f"coal:{self.path.stat().st_mtime_ns}:{self.metadata_path.stat().st_mtime_ns}"

    def load(self) -> pd.DataFrame:
        if not self.path.exists() and not self.metadata_path.exists():
            return pd.DataFrame(columns=["date", "coal_price"])
        metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        if metadata.get("schema_version") != 1 or metadata.get("unit") != "USD/t":
            raise ValueError("Formato de datos de carbon no compatible.")
        if hashlib.sha256(self.path.read_bytes()).hexdigest() != metadata["sha256"]:
            raise ValueError("El archivo de carbon no coincide con su version verificada.")
        frame = pd.read_csv(self.path, parse_dates=["date"])
        if len(frame) != metadata["rows"] or frame["date"].duplicated().any():
            raise ValueError("La serie de carbon esta incompleta o contiene duplicados.")
        return frame.sort_values("date").reset_index(drop=True)
