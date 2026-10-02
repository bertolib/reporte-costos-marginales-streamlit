"""Export Excel-shaped CMg tables from native TSV files."""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.application.services.cmg_table_builder import (
    build_excel_15min_table,
    build_excel_hourly_table,
    build_supabase_15min_table,
)
from src.infrastructure.repositories.tsv_market_repository import TsvMarketRepository


DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output" / "processed"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    repository = TsvMarketRepository(DATA_DIR)
    fifteen_minutes = build_excel_15min_table(repository)
    hourly = build_excel_hourly_table(repository)
    supabase = build_supabase_15min_table(repository)

    date_min = fifteen_minutes["Fecha"].min().strftime("%Y%m%d")
    date_max = fifteen_minutes["Fecha"].max().strftime("%Y%m%d")
    suffix = f"{date_min}_{date_max}"

    fifteen_minutes.to_csv(OUTPUT_DIR / f"cmg_15min_{suffix}.csv", index=False)
    hourly.to_csv(OUTPUT_DIR / f"cmg_hourly_{suffix}.csv", index=False)
    supabase.to_csv(
        OUTPUT_DIR / f"supabase_cmg_15min_report_data_{suffix}.csv",
        index=False,
        float_format="%.5f",
    )
    supabase.to_csv(
        OUTPUT_DIR / f"excel_review_cmg_15min_report_data_{suffix}.csv",
        index=False,
        sep=";",
        decimal=",",
        float_format="%.5f",
    )

    print(f"Exported {len(fifteen_minutes)} 15-minute rows")
    print(f"Exported {len(hourly)} hourly rows")
    print(f"Exported {len(supabase)} Supabase-ready rows")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
