"""Application settings."""

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_EXCEL_PATH = PROJECT_ROOT / "CM acumulado 2025-2026.xlsx"
GENERATION_EXCEL_PATH = PROJECT_ROOT / "Generación por tipo de tecnologia.xlsx"
DATA_SOURCE = os.getenv("DATA_SOURCE", "excel").lower()
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "cmg_15min_report_data")
APP_TITLE = "Costos Marginales Chile"
COMPANY_NAME = "Noracid S.A."
