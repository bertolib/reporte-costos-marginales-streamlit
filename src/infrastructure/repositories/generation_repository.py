"""Excel-backed generation data repository."""

from pathlib import Path

import pandas as pd


ENERGY_COLUMNS = [
    "BioGas",
    "Biomasa",
    "Carbón",
    "Cogeneracion",
    "Diésel",
    "Embalse",
    "Eólica",
    "Fuel Oil",
    "Gas Natural",
    "Geotérmica",
    "Pasada",
    "PetCoke",
    "Solar",
    "Térmica",
    "Termosolar",
    "Inyección",
    "Retiro",
    "-",
    "GLP",
]


class GenerationRepository:
    """Read generation by source from the workbook pivot sheet."""

    def __init__(self, source_path: Path) -> None:
        self.source_path = source_path

    def load_daily_generation(self) -> pd.DataFrame:
        """Return daily generation in long format."""
        df = pd.read_excel(self.source_path, sheet_name="Hoja1", header=3)
        df = df.rename(columns={"Etiquetas de fila": "date"})
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        available_columns = [column for column in ENERGY_COLUMNS if column in df.columns]
        for column in available_columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        long_df = df.melt(
            id_vars=["date"],
            value_vars=available_columns,
            var_name="energy_type",
            value_name="generation_mwh",
        )
        long_df["generation_mwh"] = long_df["generation_mwh"].fillna(0)
        return long_df.sort_values(["date", "energy_type"])

    def get_last_available_date(self) -> pd.Timestamp | None:
        """Return latest available date in the generation workbook."""
        df = self.load_daily_generation()
        if df.empty:
            return None
        return df["date"].max()
