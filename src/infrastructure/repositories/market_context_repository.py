"""Read market context from local workbooks or compact published datasets."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import pandas as pd

from config.settings import DEFAULT_EXCEL_PATH, GENERATION_EXCEL_PATH, PROJECT_ROOT, get_setting
from src.infrastructure.repositories.excel_market_repository import ExcelMarketRepository
from src.infrastructure.repositories.generation_repository import GenerationRepository


CONTEXT_DIR = PROJECT_ROOT / "database" / "market_context"
CONTEXT_FILES = {
    "generation": "generation.csv.gz",
    "daily_context": "daily_context.csv.gz",
    "projections": "projections.csv.gz",
}


@dataclass
class MarketContextData:
    generation: pd.DataFrame
    daily_context: pd.DataFrame
    projections: pd.DataFrame
    source_label: str
    exported_at: str | None = None


class MarketContextRepository:
    def __init__(self, mode: str | None = None, context_dir: Path = CONTEXT_DIR,
                 market_path: Path = DEFAULT_EXCEL_PATH,
                 generation_path: Path = GENERATION_EXCEL_PATH) -> None:
        mode = mode or str(get_setting("CONTEXT_DATA_SOURCE", "auto")).lower()
        if mode not in {"auto", "excel", "published"}:
            raise ValueError("CONTEXT_DATA_SOURCE debe ser auto, excel o published.")
        self.mode = ("excel" if market_path.exists() and generation_path.exists() else "published") if mode == "auto" else mode
        self.context_dir = context_dir
        self.market_path = market_path
        self.generation_path = generation_path

    def cache_token(self) -> str:
        paths = ([self.market_path, self.generation_path] if self.mode == "excel" else
                 [self.context_dir / "metadata.json", *[self.context_dir / name for name in CONTEXT_FILES.values()]])
        return self.mode + ":" + ":".join(f"{path}:{path.stat().st_mtime_ns}" for path in paths)

    def load(self) -> MarketContextData:
        if self.mode == "excel":
            market = ExcelMarketRepository(self.market_path)
            return MarketContextData(
                GenerationRepository(self.generation_path).load_daily_generation(),
                market.load_daily_market_context(), market.load_cen_projections(),
                "Excel locales",
            )
        manifest = json.loads((self.context_dir / "metadata.json").read_text(encoding="utf-8"))
        if manifest.get("schema_version") != 1:
            raise ValueError("Version de datos de contexto no compatible.")
        datasets = {}
        for key, filename in CONTEXT_FILES.items():
            path = self.context_dir / filename
            expected = manifest["datasets"][key]
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
                raise ValueError(f"Los datos publicados de {key} no coinciden con su version verificada.")
            frame = pd.read_csv(path)
            if len(frame) != expected["rows"]:
                raise ValueError(f"La tabla de {key} esta incompleta.")
            if "date" in frame:
                frame["date"] = pd.to_datetime(frame["date"], errors="raise")
            datasets[key] = frame
        return MarketContextData(**datasets, source_label="Datos de contexto publicados",
                                 exported_at=manifest["exported_at"])
