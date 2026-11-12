import pandas as pd
import pytest

from src.application.services.insight_service import InsightService
from src.domain.units import report_cost_unit
from src.presentation.components.charts import (
    bess_arbitrage_chart, daily_trend_chart, hourly_profile_chart,
    last_six_months_average_chart,
)


@pytest.mark.parametrize("nodes,unit", [
    (["Chaca 110"], "CLP/kWh"),
    (["Chaca 110", "Mejillones 110"], "USD/MWh"),
    (["Mejillones 110"], "USD/MWh"),
])
def test_selection_units_are_consistent_in_charts_and_insights(nodes, unit):
    observations = pd.DataFrame([
        {"timestamp": timestamp, "node_name": node, "zone": "Norte", "value": float(index % 24)}
        for node in nodes
        for index, timestamp in enumerate(pd.date_range("2026-10-01", periods=48, freq="h"))
    ])
    original = observations.copy(deep=True)
    assert report_cost_unit(observations["node_name"]) == unit
    for build_chart in (daily_trend_chart, hourly_profile_chart, last_six_months_average_chart):
        chart = build_chart(observations)
        assert chart.layout.yaxis.title.text == unit
        assert all(unit in trace.hovertemplate for trace in chart.data)
    spread = bess_arbitrage_chart(observations)
    assert spread.layout.yaxis.title.text == f"Spread bruto diario ({unit})"
    assert unit in spread.layout.annotations[0].text
    assert all(unit in trace.hovertemplate for trace in spread.data)
    assert unit in InsightService().build_initial_insights(observations)[0]
    pd.testing.assert_frame_equal(observations, original)
