"""Update the local historical Supabase-ready CSV with the current TSV data."""

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.application.services.cmg_table_builder import build_supabase_15min_table
from src.infrastructure.repositories.tsv_market_repository import TsvMarketRepository


DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output" / "processed"
KEY_COLUMNS = ["fecha", "hora", "minutos"]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    current_history_path = _find_latest_history_file()
    history = pd.read_csv(current_history_path)
    update = build_supabase_15min_table(TsvMarketRepository(DATA_DIR))

    history = _normalize_keys(history)
    update = _normalize_keys(update)

    existing_keys = set(map(tuple, history[KEY_COLUMNS].to_numpy()))
    update_keys = set(map(tuple, update[KEY_COLUMNS].to_numpy()))
    inserted = len(update_keys - existing_keys)
    updated = len(update_keys & existing_keys)

    merged = (
        pd.concat([history, update], ignore_index=True)
        .drop_duplicates(subset=KEY_COLUMNS, keep="last")
        .sort_values("timestamp")
    )

    date_min = pd.to_datetime(merged["fecha"]).min().strftime("%Y%m%d")
    date_max = pd.to_datetime(merged["fecha"]).max().strftime("%Y%m%d")
    suffix = f"{date_min}_{date_max}"
    supabase_path = OUTPUT_DIR / f"historical_supabase_cmg_15min_report_data_{suffix}.csv"
    review_path = OUTPUT_DIR / f"historical_excel_review_cmg_15min_report_data_{suffix}.csv"

    merged.to_csv(supabase_path, index=False, float_format="%.5f")
    merged.to_csv(review_path, index=False, sep=";", decimal=",", float_format="%.5f")

    print(f"Source history: {current_history_path.name}")
    print(f"Update rows: {len(update)}")
    print(f"Rows updated/replaced: {updated}")
    print(f"Rows inserted: {inserted}")
    print(f"Historical rows after update: {len(merged)}")
    print(f"Date range: {date_min} to {date_max}")
    print(f"Output: {supabase_path}")


def _find_latest_history_file() -> Path:
    candidates = sorted(
        OUTPUT_DIR.glob("historical_supabase_cmg_15min_report_data_*.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        msg = "No historical Supabase-ready CSV found in output/processed."
        raise FileNotFoundError(msg)
    return candidates[0]


def _normalize_keys(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized["fecha"] = pd.to_datetime(normalized["fecha"]).dt.strftime("%Y-%m-%d")
    normalized["hora"] = pd.to_numeric(normalized["hora"], errors="raise").astype(int)
    normalized["minutos"] = pd.to_numeric(normalized["minutos"], errors="raise").astype(int)
    normalized["timestamp"] = pd.to_datetime(normalized["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    return normalized


if __name__ == "__main__":
    main()
