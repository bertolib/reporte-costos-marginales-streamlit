"""Load the Supabase-ready CMg historical CSV into Supabase."""

from __future__ import annotations

from pathlib import Path
import math
import os
import sys
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "processed"
TABLE_NAME = "cmg_15min_report_data"
BATCH_SIZE = 1_000


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY")
    if not supabase_url or not supabase_key:
        msg = "Missing SUPABASE_URL or SUPABASE_SECRET_KEY in .env"
        raise RuntimeError(msg)

    csv_path = _find_latest_history_file()
    df = pd.read_csv(csv_path)
    records = _to_supabase_records(df)

    client = create_client(supabase_url, supabase_key)
    for start in range(0, len(records), BATCH_SIZE):
        batch = records[start : start + BATCH_SIZE]
        client.table(TABLE_NAME).upsert(
            batch,
            on_conflict="fecha,hora,minutos",
        ).execute()
        print(f"Uploaded {min(start + BATCH_SIZE, len(records))}/{len(records)} rows")

    print(f"Loaded {len(records)} rows from {csv_path.name} into {TABLE_NAME}")


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


def _to_supabase_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    clean = df.copy()
    clean["fecha"] = pd.to_datetime(clean["fecha"]).dt.strftime("%Y-%m-%d")
    clean["timestamp"] = pd.to_datetime(clean["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    clean["hora"] = pd.to_numeric(clean["hora"], errors="raise").astype(int)
    clean["minutos"] = pd.to_numeric(clean["minutos"], errors="raise").astype(int)
    clean = clean.where(pd.notna(clean), None)
    return [
        {key: _clean_value(value) for key, value in record.items()}
        for record in clean.to_dict(orient="records")
    ]


def _clean_value(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


if __name__ == "__main__":
    sys.exit(main())
