from types import SimpleNamespace

import pandas as pd
import pytest

from scripts import actualizar_web as updater


def make_day(day):
    stamps = pd.date_range(day, periods=96, freq="15min")
    frame = pd.DataFrame({"timestamp": stamps, "fecha": stamps.date,
                          "hora": stamps.hour, "minutos": stamps.minute,
                          "source_file": "test.tsv", "version": "REAL-DEF"})
    for column in updater.SUPABASE_SERIES_COLUMNS:
        frame[column] = 10.5
    return frame


@pytest.mark.parametrize("problem", ["gap", "missing", "duplicate"])
def test_invalid_input_is_rejected(problem):
    frame = make_day("2026-11-04")
    if problem == "gap":
        frame = frame.iloc[1:]
    elif problem == "missing":
        frame.loc[0, next(iter(updater.SUPABASE_SERIES_COLUMNS))] = float("nan")
    else:
        frame = pd.concat([frame, frame.iloc[:1]])
    with pytest.raises(ValueError):
        updater.validate_update(frame)


@pytest.mark.parametrize("tamper", [False, True])
def test_load_verifies_entire_history_before_replacing_snapshot(tmp_path, monkeypatch, tamper):
    before = updater._to_supabase_records(make_day("2026-11-03"))
    for record in before:
        record["loaded_at"] = "2026-11-12T12:00:00+00:00"
    state = list(before)
    update = make_day("2026-11-04")

    class Table:
        def upsert(self, batch, **kwargs):
            state.extend(batch)
            if tamper:
                state[0] = {**state[0], "cmg_mej_110_usd_mwh": 999.0}
            return self

        def execute(self):
            return None

    repository = SimpleNamespace(client=SimpleNamespace(table=lambda _: Table()), table_name="test")
    snapshot = tmp_path / "snapshot.csv.gz"
    snapshot.write_bytes(b"previous snapshot")
    metadata = tmp_path / "metadata.json"
    monkeypatch.setattr(updater, "ROOT", tmp_path)
    monkeypatch.setattr(updater, "SNAPSHOT", snapshot)
    monkeypatch.setattr(updater, "METADATA", metadata)
    monkeypatch.setattr(updater, "choose_file", lambda _: tmp_path / "test.tsv")
    monkeypatch.setattr(updater, "prepare_update", lambda _: update)
    monkeypatch.setattr(updater, "SupabaseMarketRepository", lambda: repository)
    monkeypatch.setattr(updater, "fetch_history", lambda _: pd.DataFrame(state))
    monkeypatch.setattr(updater.sys, "argv", ["actualizar_web.py"])
    if tamper:
        with pytest.raises(AssertionError):
            updater.main()
        assert snapshot.read_bytes() == b"previous snapshot"
        assert not metadata.exists()
    else:
        updater.main()
        assert len(pd.read_csv(snapshot)) == 192
        assert "2026-11-04 23:45:00" in metadata.read_text()
    backup = next((tmp_path / "output" / "processed").glob("supabase_backup_*.csv.gz"))
    assert len(pd.read_csv(backup)) == 96


def test_multiple_active_files_requires_explicit_choice(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "a.tsv").touch()
    (tmp_path / "data" / "b.tsv").touch()
    monkeypatch.setattr(updater, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="un solo TSV"):
        updater.choose_file(None)
