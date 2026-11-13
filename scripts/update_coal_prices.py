"""Import Investing.com daily Newcastle coal closes for the monthly context chart."""

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

from src.infrastructure.repositories.coal_price_repository import (
    COAL_METADATA, COAL_PATH, COAL_SOURCE, CoalPriceRepository,
)
from src.infrastructure.repositories.market_context_repository import MarketContextRepository


def read_download(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="utf-8-sig")
    if not {"Date", "Price"}.issubset(raw.columns):
        raise ValueError("El CSV de Investing debe contener Date y Price, con frecuencia diaria.")
    frame = pd.DataFrame({
        "date": pd.to_datetime(raw["Date"], format="%m/%d/%Y", errors="raise"),
        "coal_price": pd.to_numeric(raw["Price"].astype(str).str.replace(",", "", regex=False), errors="raise"),
    }).sort_values("date").reset_index(drop=True)
    if frame.empty or frame["date"].isna().any() or frame["date"].duplicated().any():
        raise ValueError("El archivo esta vacio o tiene fechas no validas o duplicadas.")
    if not np.isfinite(frame["coal_price"]).all() or (frame["coal_price"] <= 0).any():
        raise ValueError("El archivo contiene precios no validos.")
    if frame["date"].max().date() > datetime.now(timezone.utc).date():
        raise ValueError("El archivo contiene fechas futuras.")
    return frame


def merge_prices(history: pd.DataFrame, update: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    history = history[["date", "coal_price"]].dropna().copy()
    history["date"] = pd.to_datetime(history["date"])
    if history["date"].duplicated().any():
        raise ValueError("El historico tiene fechas duplicadas.")
    start, end = update["date"].min(), update["date"].max()
    if not history.empty and start > history["date"].max() + pd.Timedelta(days=10):
        raise ValueError("La descarga deja un hueco respecto al historico. Descargue un periodo mas amplio.")
    overlap = history.merge(update, on="date", suffixes=("_old", "_new"))
    revised = int((~np.isclose(overlap["coal_price_old"], overlap["coal_price_new"], rtol=0, atol=1e-8)).sum()) if not overlap.empty else 0
    # The CSV is authoritative for its date window: keep actual trading sessions,
    # rather than retaining old carried-forward weekend values inside that window.
    preserved = history[(history["date"] < start) | (history["date"] > end)]
    merged = pd.concat([preserved, update], ignore_index=True).sort_values("date").reset_index(drop=True)
    pd.testing.assert_frame_equal(merged[merged["date"].between(start, end)].reset_index(drop=True), update, check_dtype=False)
    return merged, {"overlap": len(overlap), "revised_overlap": revised,
                    "new_sessions": len(update) - len(overlap), "download_rows": len(update)}


def import_coal(path: Path, validate_only: bool = False) -> dict:
    update = read_download(path)
    history = CoalPriceRepository().load()
    if history.empty:
        history = MarketContextRepository(mode="published").load().daily_context[["date", "coal_price"]]
    merged, stats = merge_prices(history, update)
    print(f"Descarga: {len(update)} cierres, {update['date'].min():%d-%m-%Y} a {update['date'].max():%d-%m-%Y}.", flush=True)
    print(f"Fechas compartidas: {stats['overlap']}; revisadas: {stats['revised_overlap']}; sesiones nuevas: {stats['new_sessions']}.", flush=True)
    if validate_only:
        print("VALIDACION CORRECTA. No se modificaron archivos publicados ni Supabase.")
        return stats
    now = datetime.now(timezone.utc)
    backup = ROOT / "output" / "processed" / f"coal_backup_{now:%Y%m%d_%H%M%S_%f}.csv.gz"
    backup.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(backup, index=False, compression="gzip")
    metadata = {"schema_version": 1, "instrument": "Newcastle Coal Futures", "symbol": "NCFMc1",
                "unit": "USD/t", "source_url": COAL_SOURCE, "source_file": path.name,
                "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "imported_at": now.isoformat(), "coverage_start": update["date"].min().strftime("%Y-%m-%d"),
                "coverage_end": update["date"].max().strftime("%Y-%m-%d"), "rows": len(merged), **stats}
    with TemporaryDirectory(dir=COAL_PATH.parent) as temporary:
        target = Path(temporary) / COAL_PATH.name
        target_meta = Path(temporary) / COAL_METADATA.name
        merged.to_csv(target, index=False, compression={"method": "gzip", "mtime": 0})
        pd.testing.assert_frame_equal(pd.read_csv(target, parse_dates=["date"]), merged, check_dtype=False)
        metadata["sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
        target_meta.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        CoalPriceRepository(target, target_meta).load()
        target.replace(COAL_PATH)
        target_meta.replace(COAL_METADATA)
    print(f"CARBON ACTUALIZADO Y VERIFICADO. Ultima sesion: {merged['date'].max():%d-%m-%Y}. Respaldo: {backup}", flush=True)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archivo", help="Ruta del CSV; por defecto busca un unico CSV dentro de data_cme.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--solo-validar", action="store_true")
    mode.add_argument("--publicar", action="store_true")
    args = parser.parse_args()
    candidates = [Path(args.archivo)] if args.archivo else list((ROOT / "data_cme").rglob("*.csv"))
    if len(candidates) != 1 or not candidates[0].is_file():
        raise ValueError("Deje un unico CSV en data_cme o elija uno con --archivo.")
    if args.publicar:
        from scripts.actualizar_web import check_publication
        check_publication()
    import_coal(candidates[0], validate_only=args.solo_validar)
    if args.publicar:
        from scripts.actualizar_web import git
        git("add", "database/market_context/coal_prices.csv.gz", "database/market_context/coal_metadata.json")
        if git("diff", "--cached", "--name-only"):
            git("commit", "-m", "Refresh Newcastle coal closes for market context")
            git("push", "origin", "main")
        print("CARBON PUBLICADO EN GITHUB.")


if __name__ == "__main__":
    main()
