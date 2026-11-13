"""Export only the market-context tables needed by Streamlit Cloud."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.infrastructure.repositories.market_context_repository import (
    CONTEXT_DIR, CONTEXT_FILES, MarketContextRepository,
)


def validate_context(datasets: dict[str, pd.DataFrame]) -> None:
    required = {
        "generation": ["date", "energy_type", "generation_mwh"],
        "daily_context": ["date", "daily_cmg", "monthly_average_cmg", "cen_monthly_projection", "coal_price", "oil_price"],
        "projections": ["projection_month"],
    }
    for key, columns in required.items():
        frame = datasets[key]
        if frame.empty or not set(columns).issubset(frame.columns):
            raise ValueError(f"Faltan datos o columnas en {key}.")
    generation = datasets["generation"]
    if generation.duplicated(["date", "energy_type"]).any():
        raise ValueError("Existen registros de generacion duplicados.")
    if not np.isfinite(generation["generation_mwh"]).all():
        raise ValueError("La generacion contiene valores no validos.")
    if datasets["daily_context"]["date"].duplicated().any():
        raise ValueError("Existen fechas duplicadas en el contexto diario.")
    if datasets["projections"]["projection_month"].duplicated().any():
        raise ValueError("Existen meses de emision duplicados en las proyecciones.")


def export_context(destination: Path = CONTEXT_DIR) -> dict:
    print("Leyendo tablas de contexto desde los Excel locales...", flush=True)
    context = MarketContextRepository(mode="excel").load()
    datasets = {key: getattr(context, key).reset_index(drop=True) for key in CONTEXT_FILES}
    for key, text_columns in {"generation": ["date", "energy_type"],
                              "daily_context": ["date"],
                              "projections": ["projection_month"]}.items():
        numeric_columns = datasets[key].columns.drop(text_columns)
        datasets[key][numeric_columns] = datasets[key][numeric_columns].apply(pd.to_numeric, errors="raise")
    validate_context(datasets)
    manifest = {"schema_version": 1, "exported_at": datetime.now(timezone.utc).isoformat(),
                "sources": {}, "datasets": {}}
    for path in (MarketContextRepository(mode="excel").market_path,
                 MarketContextRepository(mode="excel").generation_path):
        manifest["sources"][path.name] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as temporary:
        staging = Path(temporary)
        for key, filename in CONTEXT_FILES.items():
            frame = datasets[key]
            path = staging / filename
            frame.to_csv(path, index=False, compression={"method": "gzip", "mtime": 0})
            recovered = pd.read_csv(path)
            if "date" in recovered:
                recovered["date"] = pd.to_datetime(recovered["date"])
            pd.testing.assert_frame_equal(recovered, frame, check_dtype=False, rtol=1e-12, atol=1e-9)
            manifest["datasets"][key] = {
                "rows": len(frame), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
            if "date" in frame:
                manifest["datasets"][key]["date_min"] = frame["date"].min().strftime("%Y-%m-%d")
                manifest["datasets"][key]["date_max"] = frame["date"].max().strftime("%Y-%m-%d")
            print(f"Verificado {key}: {len(frame)} filas; {path.stat().st_size:,} bytes", flush=True)
        (staging / "metadata.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        # Verify exactly what the deployed app will read before replacing published files.
        MarketContextRepository(mode="published", context_dir=staging).load()
        destination.mkdir(parents=True, exist_ok=True)
        for name in [*CONTEXT_FILES.values(), "metadata.json"]:
            (staging / name).replace(destination / name)
    print(f"CONTEXTO EXPORTADO Y VERIFICADO: {destination}", flush=True)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--publicar", action="store_true", help="Publicar solo los datos de contexto en GitHub.")
    mode.add_argument("--solo-validar", action="store_true", help="Validar los Excel sin cambiar datos publicados ni conectar a Supabase.")
    args = parser.parse_args()
    if args.solo_validar:
        with TemporaryDirectory() as temporary:
            export_context(Path(temporary) / "context")
        print("VALIDACION CORRECTA. No se modificaron los datos publicados ni Supabase.")
        return
    if args.publicar:
        from scripts.actualizar_web import check_publication
        check_publication()
    export_context()
    if args.publicar:
        from scripts.actualizar_web import git
        git("add", "database/market_context")
        if git("diff", "--cached", "--name-only"):
            git("commit", "-m", "Refresh published electric market context")
            git("push", "origin", "main")
        print("CONTEXTO PUBLICADO EN GITHUB.")


if __name__ == "__main__":
    main()
