import pandas as pd
import pytest
from httpx import ConnectError

from src.presentation import app


@pytest.mark.parametrize("failure_stage", ["token", "hourly", "detail"])
def test_database_outage_uses_snapshot_for_entire_report(monkeypatch, failure_stage):
    hourly = pd.DataFrame({"scenario": ["actual"], "value": [10.0]})
    detail = pd.DataFrame({"scenario": ["actual"], "value": [20.0]})
    tokens = []

    def source_token():
        if failure_stage == "token":
            raise ConnectError("Database unavailable")
        return "live"

    def load(token, stage, frame):
        tokens.append((token, stage))
        if token == "live" and stage == failure_stage:
            raise ConnectError("Database unavailable")
        return frame

    monkeypatch.setattr(app, "DATA_SOURCE", "supabase")
    monkeypatch.setattr(app, "_source_token", source_token)
    monkeypatch.setattr(app, "_load_hourly_data", lambda token: load(token, "hourly", hourly))
    monkeypatch.setattr(app, "_load_fifteen_minutes_data", lambda token: load(token, "detail", detail))
    actual_hourly, actual_detail, is_snapshot = app._load_report_data(True)
    assert is_snapshot
    pd.testing.assert_frame_equal(actual_hourly, hourly)
    pd.testing.assert_frame_equal(actual_detail, detail)
    assert tokens[-2][0].startswith("snapshot:")
    assert tokens[-1][0].startswith("snapshot:")


def test_database_recovery_returns_to_live_data(monkeypatch):
    frame = pd.DataFrame({"scenario": ["actual"], "value": [10.0]})
    monkeypatch.setattr(app, "_source_token", lambda: "live")
    monkeypatch.setattr(app, "_load_hourly_data", lambda _: frame)
    _, detail, is_snapshot = app._load_report_data(False)
    assert not is_snapshot
    assert detail is None
