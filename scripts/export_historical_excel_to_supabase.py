"""Export historical CMg report data from the parent Excel workbook."""

from pathlib import Path
import sys
from datetime import datetime, time

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.application.services.cmg_table_builder import EXCEL_COST_COLUMNS


EXCEL_PATH = PROJECT_ROOT / "CM acumulado 2025-2026.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "output" / "processed"
SHEET_NAME = "Datos CMg 15min"

EXCEL_TO_SUPABASE_COLUMNS = {
    "Cmg Mej 110 (USD/MWh)": "cmg_mej_110_usd_mwh",
    "Cmg Chaca 110 (CLP)": "cmg_chaca_110_clp_kwh",
    "Cmg Chacaya 110 (USD/MWh)": "cmg_chacaya_110_usd_mwh",
    "Alto Jahuel 220 (USD/MWh)": "alto_jahuel_220_usd_mwh",
    "Charrua 220 (USD/MWh)": "charrua_220_usd_mwh",
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    historical = build_historical_supabase_table(EXCEL_PATH)
    date_min = historical["fecha"].min().strftime("%Y%m%d")
    date_max = historical["fecha"].max().strftime("%Y%m%d")
    suffix = f"{date_min}_{date_max}"

    historical.to_csv(
        OUTPUT_DIR / f"historical_supabase_cmg_15min_report_data_{suffix}.csv",
        index=False,
        float_format="%.5f",
    )
    historical.to_csv(
        OUTPUT_DIR / f"historical_excel_review_cmg_15min_report_data_{suffix}.csv",
        index=False,
        sep=";",
        decimal=",",
        float_format="%.5f",
    )

    print(f"Exported {len(historical)} historical Supabase-ready rows")
    print(f"Date range: {historical['fecha'].min()} to {historical['fecha'].max()}")
    print(f"Output directory: {OUTPUT_DIR}")


def build_historical_supabase_table(excel_path: Path) -> pd.DataFrame:
    """Read the first 15-minute table in the parent workbook."""
    raw = pd.read_excel(excel_path, sheet_name=SHEET_NAME)
    table = raw.iloc[:, :12].copy()
    table.columns = [
        "idx",
        "Mes",
        "Fecha",
        "Anio",
        "Hora",
        "Minutos",
        *EXCEL_COST_COLUMNS,
        "Proyeccion CMG",
    ]

    table["Fecha"] = pd.to_datetime(table["Fecha"], errors="coerce")
    table["Hora"] = pd.to_numeric(table["Hora"], errors="coerce")
    display_minute = table["Minutos"].map(_extract_display_minute)

    for column in EXCEL_COST_COLUMNS:
        table[column] = pd.to_numeric(table[column], errors="coerce")

    table = table[table[EXCEL_COST_COLUMNS].notna().any(axis=1)].copy()
    display_minute = display_minute.loc[table.index]
    native_hour = table["Hora"].where(display_minute.ne(0), table["Hora"] - 1)
    native_minute = display_minute.where(display_minute.ne(0), 60) - 15

    output = table.rename(columns=EXCEL_TO_SUPABASE_COLUMNS)
    output["fecha"] = table["Fecha"].dt.date
    output["hora"] = native_hour.astype(int)
    output["minutos"] = native_minute.astype(int)
    output["timestamp"] = (
        table["Fecha"]
        + pd.to_timedelta(output["hora"], unit="h")
        + pd.to_timedelta(output["minutos"], unit="m")
    )
    output["source_file"] = excel_path.name
    output["version"] = "excel-parent"

    return output[
        [
            "fecha",
            "hora",
            "minutos",
            "timestamp",
            "cmg_mej_110_usd_mwh",
            "cmg_chaca_110_clp_kwh",
            "cmg_chacaya_110_usd_mwh",
            "alto_jahuel_220_usd_mwh",
            "charrua_220_usd_mwh",
            "source_file",
            "version",
        ]
    ].sort_values("timestamp")


def _extract_display_minute(value: object) -> int:
    if isinstance(value, time):
        return value.minute
    if isinstance(value, datetime):
        return value.minute
    if isinstance(value, str):
        parts = value.split(":")
        if len(parts) >= 2:
            return int(parts[1])
    if pd.isna(value):
        return 0
    parsed = pd.to_datetime(str(value), format="%H:%M:%S", errors="coerce")
    if pd.isna(parsed):
        return 0
    return int(parsed.minute)


if __name__ == "__main__":
    main()
