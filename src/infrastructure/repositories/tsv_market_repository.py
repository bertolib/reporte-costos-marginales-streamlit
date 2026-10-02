"""TSV-backed market data repository for native CEN downloads."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.domain.enums import Granularity, Scenario
from src.domain.node_catalog import NODE_CATALOG
from src.infrastructure.repositories.market_repository import MarketRepository


@dataclass(frozen=True)
class TsvSeries:
    """Mapping from a native TSV bar/value column to a canonical series."""

    node_id: str
    bar_code: str
    value_column: str
    unit: str


SELECTED_TSV_SERIES: tuple[TsvSeries, ...] = (
    TsvSeries("cmg_mej_110", "MEJILLONES____110", "CMg[USD/MWh]", "USD/MWh"),
    TsvSeries("cmg_chaca_110_clp", "CHACAYA_______110", "CMg[CLP/KWh]", "CLP/KWh"),
    TsvSeries("cmg_chacaya_110", "CHACAYA_______110", "CMg[USD/MWh]", "USD/MWh"),
    TsvSeries("alto_jahuel_220", "A.JAHUEL______220", "CMg[USD/MWh]", "USD/MWh"),
    TsvSeries("charrua_220", "CHARRUA_______220", "CMg[USD/MWh]", "USD/MWh"),
)


class TsvMarketRepository(MarketRepository):
    """Read marginal-cost observations from native monthly TSV files."""

    def __init__(self, source_path: Path, chunk_size: int = 250_000) -> None:
        self.source_path = source_path
        self.chunk_size = chunk_size

    def load_observations(self, granularity: Granularity) -> pd.DataFrame:
        """Return selected observations in canonical long format."""
        if granularity not in {Granularity.FIFTEEN_MINUTES, Granularity.HOURLY}:
            msg = f"Unsupported TSV granularity: {granularity}"
            raise ValueError(msg)

        observations = self._load_fifteen_minutes()
        if granularity == Granularity.FIFTEEN_MINUTES:
            return observations
        return self._to_hourly(observations)

    def get_last_update(self) -> pd.Timestamp | None:
        """Return latest timestamp available in the TSV source."""
        observations = self.load_observations(Granularity.FIFTEEN_MINUTES)
        if observations.empty:
            return None
        return observations["timestamp"].max()

    def _load_fifteen_minutes(self) -> pd.DataFrame:
        frames = [self._read_tsv_file(path) for path in self._iter_tsv_files()]
        frames = [frame for frame in frames if not frame.empty]
        if not frames:
            return self._empty_observations()
        return pd.concat(frames, ignore_index=True).sort_values(["timestamp", "node_name", "unit"])

    def _iter_tsv_files(self) -> list[Path]:
        if self.source_path.is_file():
            return [self.source_path]
        return sorted(self.source_path.glob("*.tsv"))

    def _read_tsv_file(self, path: Path) -> pd.DataFrame:
        selected_codes = {series.bar_code for series in SELECTED_TSV_SERIES}
        frames: list[pd.DataFrame] = []
        usecols = [
            "BARRA_TRANSF",
            "FECHA",
            "HRA",
            "MIN",
            "CMg[USD/MWh]",
            "CMg[CLP/KWh]",
            "VERSION",
        ]
        for chunk in pd.read_csv(path, sep="\t", usecols=usecols, chunksize=self.chunk_size):
            chunk = chunk[chunk["BARRA_TRANSF"].isin(selected_codes)].copy()
            if chunk.empty:
                continue
            frames.append(self._canonicalize_chunk(chunk, path.name))

        if not frames:
            return self._empty_observations()
        return pd.concat(frames, ignore_index=True)

    def _canonicalize_chunk(self, chunk: pd.DataFrame, source_name: str) -> pd.DataFrame:
        frames = []
        for series in SELECTED_TSV_SERIES:
            native = chunk[chunk["BARRA_TRANSF"] == series.bar_code].copy()
            if native.empty:
                continue
            node = NODE_CATALOG[series.node_id]
            frame = pd.DataFrame(
                {
                    "timestamp": self._build_timestamp(native),
                    "node_id": series.node_id,
                    "node_name": node.name,
                    "zone": node.zone,
                    "value": pd.to_numeric(native[series.value_column], errors="coerce"),
                    "unit": series.unit,
                    "granularity": Granularity.FIFTEEN_MINUTES.value,
                    "scenario": Scenario.ACTUAL.value,
                    "source": source_name,
                }
            )
            frames.append(frame.dropna(subset=["timestamp", "value"]))

        if not frames:
            return self._empty_observations()
        return pd.concat(frames, ignore_index=True)

    @staticmethod
    def _build_timestamp(df: pd.DataFrame) -> pd.Series:
        base_date = pd.to_datetime(df["FECHA"], errors="coerce")
        hour = pd.to_numeric(df["HRA"], errors="coerce").fillna(0).astype(int)
        minute = pd.to_numeric(df["MIN"], errors="coerce").fillna(0).astype(int)
        return base_date + pd.to_timedelta(hour, unit="h") + pd.to_timedelta(minute, unit="m")

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
