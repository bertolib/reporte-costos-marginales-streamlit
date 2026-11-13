from datetime import date
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from scripts import export_market_context as exporter
from src.infrastructure.repositories.market_context_repository import (
    CONTEXT_DIR, CONTEXT_FILES, MarketContextData, MarketContextRepository,
)


def test_cloud_reads_published_data_without_local_workbooks(monkeypatch, tmp_path):
    def no_excel(*args, **kwargs):
        raise AssertionError("Cloud must not read an Excel workbook")

    monkeypatch.setattr(pd, "read_excel", no_excel)
    repository = MarketContextRepository(mode="auto", market_path=tmp_path / "missing.xlsx",
                                         generation_path=tmp_path / "also_missing.xlsx")
    assert repository.mode == "published"
    context = repository.load()
    assert not context.generation.empty
    assert not context.daily_context.empty
    assert not context.projections.empty
    assert context.generation["date"].notna().all()


def test_published_context_rejects_incomplete_or_mixed_export(tmp_path):
    shutil.copytree(CONTEXT_DIR, tmp_path / "context")
    path = tmp_path / "context" / CONTEXT_FILES["generation"]
    path.write_bytes(path.read_bytes() + b"modified")
    with pytest.raises(ValueError, match="version verificada"):
        MarketContextRepository(mode="published", context_dir=tmp_path / "context").load()


def test_export_preserves_dates_numeric_precision_and_missing_projections(tmp_path, monkeypatch):
    market, generation = tmp_path / "market.xlsx", tmp_path / "generation.xlsx"
    market.write_bytes(b"source market")
    generation.write_bytes(b"source generation")
    context = MarketContextData(
        pd.DataFrame({"date": pd.to_datetime(["2026-03-04"]), "energy_type": ["Solar"], "generation_mwh": [1234.567891234]}),
        pd.DataFrame({"date": pd.to_datetime(["2026-09-21"]), "daily_cmg": [2.3456789],
                      "monthly_average_cmg": [20.0], "cen_monthly_projection": [None],
                      "coal_price": [None], "oil_price": [None]}),
        pd.DataFrame({"projection_month": ["ago-26", "jul-26"], "nov-26": [18.58, None]}),
        "Excel locales",
    )
    real_repository = exporter.MarketContextRepository

    def repository(mode, **kwargs):
        if mode == "excel":
            return SimpleNamespace(load=lambda: context, market_path=market, generation_path=generation)
        return real_repository(mode=mode, **kwargs)

    monkeypatch.setattr(exporter, "MarketContextRepository", repository)
    destination = tmp_path / "published"
    exporter.export_context(destination)
    restored = real_repository(mode="published", context_dir=destination).load()
    assert restored.generation.iloc[0]["generation_mwh"] == pytest.approx(1234.567891234)
    assert restored.daily_context.iloc[0]["date"] == pd.Timestamp("2026-09-21")
    assert pd.isna(restored.projections.iloc[1]["nov-26"])


def test_context_page_renders_and_filters_without_excel(monkeypatch):
    monkeypatch.setenv("CONTEXT_DATA_SOURCE", "published")
    script = '''
from src.presentation import app
from src.infrastructure.repositories.snapshot_market_repository import SnapshotMarketRepository
app._source_token = lambda: "context-cloud-test"
app._repository = lambda *args: SnapshotMarketRepository()
app.run_app()
'''
    at = AppTest.from_string(script, default_timeout=45).run()
    at.sidebar.radio[0].set_value("Contexto Mercado Electrico").run()
    assert not at.exception
    assert not at.error
    assert len(at.get("plotly_chart")) == 4
    assert any("Datos de generación disponibles hasta" in item.value for item in at.caption)
    at.multiselect(key="context_energy_types").set_value(["Solar"])
    at.date_input(key="context_generation_period").set_value((date(2026, 1, 1), date(2026, 2, 1))).run()
    assert not at.exception
    chart = json.loads(at.get("plotly_chart")[0].proto.spec)
    assert [trace["name"] for trace in chart["data"]] == ["Solar"]
    at.multiselect(key="cen_projection_target_months").set_value(["oct-26", "nov-26"]).run()
    assert not at.exception
    evolution = json.loads(at.get("plotly_chart")[-1].proto.spec)
    names = [trace["name"] for trace in evolution["data"]]
    assert "Real oct-26" in names
    assert "Real nov-26" in names
