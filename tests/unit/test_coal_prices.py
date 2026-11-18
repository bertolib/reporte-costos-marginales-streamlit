from types import SimpleNamespace

import pandas as pd
import pytest

from scripts import update_coal_prices as updater
from src.infrastructure.repositories.coal_price_repository import CoalPriceRepository
from src.presentation.components.charts import monthly_cmg_coal_chart
from src.presentation.pages.marginal_costs import _monthly_context_caption


def test_download_parses_us_dates_and_prices(tmp_path):
    path = tmp_path / "download.csv"
    path.write_text('Date,Price\n11/12/2026,"1,234.50"\n01/02/2026,106.55\n', encoding="utf-8-sig")
    data = updater.read_download(path)
    assert data.date.tolist() == [pd.Timestamp("2026-01-02"), pd.Timestamp("2026-11-12")]
    assert data.coal_price.tolist() == [106.55, 1234.50]


@pytest.mark.parametrize("rows", [
    "01/02/2026,10\n01/02/2026,11\n",
    "01/02/2026,\n", "01/02/2026,-1\n",
])
def test_download_rejects_duplicates_and_invalid_prices(tmp_path, rows):
    path = tmp_path / "invalid.csv"
    path.write_text("Date,Price\n" + rows)
    with pytest.raises(ValueError):
        updater.read_download(path)


def test_merge_replaces_covered_sessions_and_preserves_outside_history():
    history = pd.DataFrame({"date": pd.to_datetime(["2025-12-31", "2026-01-02", "2026-01-03", "2026-01-05", "2026-01-06"]),
                            "coal_price": [9., 10., 10., 11., 14.]})
    update = pd.DataFrame({"date": pd.to_datetime(["2026-01-02", "2026-01-05"]), "coal_price": [12., 13.]})
    result, stats = updater.merge_prices(history, update)
    assert result.coal_price.tolist() == [9., 12., 13., 14.]
    assert pd.Timestamp("2026-01-03") not in result.date.tolist()
    assert stats["revised_overlap"] == 2
    assert stats["new_sessions"] == 0


def test_download_cannot_leave_a_large_gap_after_history():
    history = pd.DataFrame({"date": pd.to_datetime(["2026-03-04"]), "coal_price": [131.]})
    update = pd.DataFrame({"date": pd.to_datetime(["2026-10-12"]), "coal_price": [149.35]})
    with pytest.raises(ValueError, match="hueco"):
        updater.merge_prices(history, update)


def test_chart_uses_one_axis_and_keeps_monthly_coal_after_last_cmg():
    daily = pd.DataFrame({"date": pd.to_datetime(["2026-09-21"]),
                          "monthly_average_cmg": [20.], "coal_price": [100.]})
    coal = pd.DataFrame({"date": pd.to_datetime(["2026-11-12"]), "coal_price": [145.]})
    figure = monthly_cmg_coal_chart(daily, coal)
    assert list(figure.data[0].x) == [pd.Timestamp("2026-09-01"), pd.Timestamp("2026-11-01")]
    assert figure.data[0].y[0] == 20
    assert pd.isna(figure.data[0].y[-1])
    assert figure.data[1].y[-1] == 145
    assert "USD/MWh" in figure.data[0].hovertemplate
    assert "USD/t" in figure.data[1].hovertemplate
    assert "yaxis2" not in figure.layout.to_plotly_json()
    assert figure.data[1].line.dash == "dash"
    assert figure.layout.yaxis.title.text == "Valor numérico · unidad según serie"
    assert "12-11-2026" in _monthly_context_caption(daily, coal)


def test_monthly_means_and_common_base_100_do_not_modify_original_values():
    daily = pd.DataFrame({"date": pd.to_datetime(["2026-09-01", "2026-09-02", "2026-10-01"]),
                          "monthly_average_cmg": [10., 30., 40.]})
    coal = pd.DataFrame({"date": pd.to_datetime(["2026-09-03", "2026-09-04", "2026-10-02", "2026-11-12"]),
                         "coal_price": [100., 200., 300., 145.]})
    original = monthly_cmg_coal_chart(daily, coal)
    assert list(original.data[0].y[:2]) == [20., 40.]
    assert list(original.data[1].y) == [150., 300., 145.]
    indexed = monthly_cmg_coal_chart(daily, coal, comparison_mode="index")
    assert list(indexed.data[0].y[:2]) == [100., 200.]
    assert pd.isna(indexed.data[0].y[-1])
    assert list(indexed.data[1].y[:2]) == [100., 200.]
    assert indexed.layout.meta["base_month"] == "2026-09"
    assert daily.monthly_average_cmg.tolist() == [10., 30., 40.]
    assert coal.coal_price.tolist() == [100., 200., 300., 145.]


def test_import_is_verified_and_dry_run_does_not_write(tmp_path, monkeypatch):
    path = tmp_path / "download.csv"
    path.write_text("Date,Price\n01/02/2026,106.55\n01/05/2026,106.20\n")
    coal_path, metadata = tmp_path / "coal.csv.gz", tmp_path / "coal_metadata.json"
    history = pd.DataFrame({"date": pd.to_datetime(["2025-12-31", "2026-01-02"]), "coal_price": [96.48, 96.48]})
    real_repository = CoalPriceRepository
    monkeypatch.setattr(updater, "CoalPriceRepository", lambda *args: real_repository(*(args or (coal_path, metadata))))
    monkeypatch.setattr(updater, "MarketContextRepository", lambda **_: SimpleNamespace(load=lambda: SimpleNamespace(daily_context=history)))
    monkeypatch.setattr(updater, "COAL_PATH", coal_path)
    monkeypatch.setattr(updater, "COAL_METADATA", metadata)
    monkeypatch.setattr(updater, "ROOT", tmp_path)
    updater.import_coal(path, validate_only=True)
    assert not coal_path.exists() and not metadata.exists()
    assert not (tmp_path / "output").exists()
    updater.import_coal(path)
    restored = real_repository(coal_path, metadata).load()
    assert restored.coal_price.tolist() == [96.48, 106.55, 106.20]
    assert list((tmp_path / "output" / "processed").glob("coal_backup_*.csv.gz"))
