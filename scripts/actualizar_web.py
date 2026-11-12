"""Validate a CEN TSV, update Supabase, and refresh the verified web snapshot."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.load_to_supabase import _to_supabase_records
from src.application.services.cmg_table_builder import build_supabase_15min_table
from src.domain.enums import Granularity
from src.infrastructure.repositories.supabase_market_repository import (
    SUPABASE_SERIES_COLUMNS, SupabaseMarketRepository,
)
from src.infrastructure.repositories.tsv_market_repository import TsvMarketRepository

KEYS = ["fecha", "hora", "minutos"]
SNAPSHOT = ROOT / "database" / "snapshots" / "cmg_verified.csv.gz"
METADATA = SNAPSHOT.with_name("metadata.json")


def choose_file(filename: str | None) -> Path:
    if filename:
        path = Path(filename)
        path = path if path.is_absolute() else ROOT / path
        if not path.is_file() or path.suffix.lower() != ".tsv":
            raise ValueError("El archivo indicado no existe o no es TSV.")
        return path
    files = list((ROOT / "data").glob("*.tsv"))
    if len(files) != 1:
        raise ValueError("Debe haber un solo TSV en data. Use --archivo para elegir uno.")
    return files[0]


def prepare_update(path: Path) -> pd.DataFrame:
    observations = TsvMarketRepository(path).load_observations(Granularity.FIFTEEN_MINUTES)
    if observations.duplicated(["timestamp", "node_id"]).any():
        raise ValueError("El TSV contiene observaciones duplicadas para una barra e instante.")
    # Reuse the already parsed observations rather than reading the large TSV twice.
    repository = TsvMarketRepository(path)
    repository.load_observations = lambda _: observations
    update = build_supabase_15min_table(repository)
    validate_update(update)
    return update


def validate_update(update: pd.DataFrame) -> None:
    if update.empty or update.duplicated(KEYS).any():
        raise ValueError("No hay datos validos o existen registros duplicados.")
    if not np.isfinite(update[list(SUPABASE_SERIES_COLUMNS)].to_numpy(dtype=float)).all():
        raise ValueError("Faltan valores validos de alguna de las cinco series.")
    timestamps = pd.DatetimeIndex(pd.to_datetime(update["timestamp"])).sort_values()
    expected = pd.date_range(timestamps.min().normalize(),
                             timestamps.max().normalize() + pd.Timedelta(hours=23, minutes=45),
                             freq="15min")
    if not timestamps.equals(expected):
        raise ValueError("El periodo tiene dias incompletos o intervalos faltantes de 15 minutos.")


def fetch_history(repository: SupabaseMarketRepository) -> pd.DataFrame:
    def page(start: int, count: bool = False):
        return (repository.client.table(repository.table_name)
                .select("*", **({"count": "exact"} if count else {}))
                .order("timestamp").range(start, start + 999).execute())
    first = page(0, count=True)
    if first.count is None:
        raise RuntimeError("No se pudo determinar el total de registros en Supabase.")
    rows = list(first.data or [])
    with ThreadPoolExecutor(max_workers=4) as executor:
        for response in executor.map(page, range(1000, first.count, 1000)):
            rows.extend(response.data or [])
    if len(rows) != first.count:
        raise RuntimeError("La lectura de Supabase quedo incompleta. No continuar.")
    columns = [*KEYS, "timestamp", *SUPABASE_SERIES_COLUMNS, "source_file", "version", "loaded_at"]
    return pd.DataFrame(rows, columns=columns)


def normalize(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["fecha"] = pd.to_datetime(result["fecha"]).dt.strftime("%Y-%m-%d")
    result["timestamp"] = pd.to_datetime(result["timestamp"], format="mixed")
    result["loaded_at"] = pd.to_datetime(result["loaded_at"], utc=True, format="mixed")
    return result.set_index(KEYS).sort_index()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def check_publication() -> None:
    if git("branch", "--show-current") != "main" or git("status", "--porcelain"):
        raise RuntimeError("Para publicar el respaldo, use main sin cambios pendientes en Git.")
    git("fetch", "origin", "main")
    if git("rev-parse", "HEAD") != git("rev-parse", "origin/main"):
        raise RuntimeError("La copia local y origin/main deben estar sincronizadas antes de publicar.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archivo", help='Ruta TSV; por defecto busca un unico archivo en data.')
    parser.add_argument("--solo-validar", action="store_true", help="Valida sin conectar ni modificar Supabase.")
    parser.add_argument("--publicar-respaldo", action="store_true", help="Envia el respaldo verificado a GitHub.")
    args = parser.parse_args()
    path = choose_file(args.archivo)
    print(f"Validando: {path.name}", flush=True)
    update = prepare_update(path)
    latest = pd.Timestamp(update["timestamp"].max())
    print(f"Archivo valido: {len(update)} registros; {update['timestamp'].min()} a {latest}.", flush=True)
    if args.solo_validar:
        print("VALIDACION CORRECTA. No se modificaron datos.")
        return
    if args.publicar_respaldo:
        check_publication()
    repository = SupabaseMarketRepository()
    print("Leyendo y respaldando el historico de Supabase...", flush=True)
    before = fetch_history(repository)
    now = datetime.now(timezone.utc)
    output = ROOT / "output" / "processed"
    output.mkdir(parents=True, exist_ok=True)
    backup = output / f"supabase_backup_{now:%Y%m%d_%H%M%S_%f}.csv.gz"
    before.to_csv(backup, index=False, compression="gzip")
    print(f"Respaldo previo: {backup}", flush=True)
    records = _to_supabase_records(update)
    for record in records:
        record["loaded_at"] = now.isoformat()
    expected = pd.concat([before, pd.DataFrame(records)], ignore_index=True)
    expected["fecha"] = pd.to_datetime(expected["fecha"]).dt.strftime("%Y-%m-%d")
    expected = expected.drop_duplicates(KEYS, keep="last")
    print(f"Registros nuevos: {len(expected) - len(before)}; resto del archivo actualiza registros existentes.", flush=True)
    for start in range(0, len(records), 1000):
        repository.client.table(repository.table_name).upsert(
            records[start:start + 1000], on_conflict=",".join(KEYS)).execute()
        print(f"Cargados {min(start + 1000, len(records))}/{len(records)}", flush=True)
    after = fetch_history(repository)
    pd.testing.assert_frame_equal(normalize(after), normalize(expected), check_like=True,
                                  check_dtype=False, check_exact=False, rtol=0, atol=1e-6)
    # Publish backups only after checking both updated and untouched historical rows.
    snapshot_columns = ["timestamp", "source_file", "loaded_at", *SUPABASE_SERIES_COLUMNS]
    snapshot = after[snapshot_columns].copy()
    temporary = SNAPSHOT.with_name("cmg_verified.pending.csv.gz")
    snapshot.to_csv(temporary, index=False, compression={"method": "gzip", "mtime": 0})
    pd.testing.assert_frame_equal(pd.read_csv(temporary), snapshot, check_dtype=False)
    temporary.replace(SNAPSHOT)
    cutoff = pd.to_datetime(after["timestamp"], format="mixed").max()
    metadata = {"data_loaded_date_local": now.astimezone(ZoneInfo("America/Santiago")).date().isoformat(),
                "latest_observation": cutoff.strftime("%Y-%m-%d %H:%M:%S")}
    METADATA.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    start = pd.to_datetime(after["fecha"]).min().strftime("%Y%m%d")
    end = cutoff.strftime("%Y%m%d")
    history_columns = [column for column in after if column != "loaded_at"]
    after[history_columns].to_csv(output / f"historical_supabase_cmg_15min_report_data_{start}_{end}.csv", index=False)
    print(f"DATOS ACTUALIZADOS Y VERIFICADOS: {len(after)} registros historicos; hasta {cutoff}.", flush=True)
    if args.publicar_respaldo:
        git("add", "database/snapshots/cmg_verified.csv.gz", "database/snapshots/metadata.json")
        if git("diff", "--cached", "--name-only"):
            git("commit", "-m", f"Refresh verified report snapshot through {cutoff:%Y-%m-%d}")
            try:
                git("push", "origin", "main")
            except subprocess.CalledProcessError:
                raise RuntimeError("Los datos SI se cargaron en Supabase, pero fallo el envio del respaldo. Reintente git push origin main.") from None
        print("RESPALDO PUBLICADO EN GITHUB.")
    else:
        print("Respaldo renovado localmente. Para publicarlo, revise los cambios de Git y envie los dos archivos de database/snapshots.")
    print("Recargue Streamlit. Las correcciones dentro del mismo periodo pueden tardar hasta 5 minutos en reflejarse.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Do not print credentials, connection strings or raw server responses.
        print(f"ERROR ({type(error).__name__}). El proceso no termino correctamente.", file=sys.stderr)
        if isinstance(error, (ValueError, RuntimeError)):
            print(str(error), file=sys.stderr)
        print("Si la carga ya habia comenzado, algunos lotes pueden haberse aplicado. Conserve el respaldo previo y vuelva a ejecutar el mismo archivo.", file=sys.stderr)
        sys.exit(1)
