"""Application settings."""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def get_setting(name: str, default: Any = None) -> Any:
    """Read config from environment, then Streamlit Cloud secrets."""
    value = os.getenv(name)
    if value is not None:
        return value

    try:
        import streamlit as st

        return st.secrets.get(name, default)
    except Exception:
        return default

DEFAULT_EXCEL_PATH = PROJECT_ROOT / "CM acumulado 2025-2026.xlsx"
GENERATION_EXCEL_PATH = PROJECT_ROOT / "Generación por tipo de tecnologia.xlsx"
DATA_SOURCE = str(get_setting("DATA_SOURCE", "excel")).lower()
SUPABASE_TABLE = get_setting("SUPABASE_TABLE", "cmg_15min_report_data")
APP_TITLE = "Costos Marginales Chile"
COMPANY_NAME = "Noracid S.A."
