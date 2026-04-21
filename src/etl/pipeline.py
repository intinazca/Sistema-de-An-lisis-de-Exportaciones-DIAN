"""
Pipeline ETL principal.
Estrategia: chunked reading + transacciones por lote para no saturar memoria.
Con 629K filas y 109 columnas el DataFrame completo pesa ~2GB en RAM.
"""
import glob
import sys
from pathlib import Path

import pandas as pd
from loguru import logger

from src.config import settings
from src.db.init_db import create_tables, create_analytical_views, refresh_materialized_views
from src.db.session import get_db
from src.etl.cleaner import clean_declaraciones, clean_series
from src.etl.column_map import DECLARACION_COLS, SERIE_COLS
from src.etl.loader import PostgresLoader

logger.remove()
logger.add(sys.stderr, level=settings.log_level, format="{time:HH:mm:ss} | {level} | {message}")
logger.add("etl_run.log", rotation="10 MB", level="DEBUG")


def _rename_columns(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    existing = {k: v for k, v in col_map.items() if k in df.columns}
    return df.rename(columns=existing)


def _split_declaraciones_series(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Cada fila del XLSX es una SERIE. Para obtener declaraciones únicas
    deduplicamos por num_formulario conservando los campos de cabecera.
    """
    decl_internal_cols = list(DECLARACION_COLS.values())
    serie_internal_cols = list(SERIE_COLS.values())

    available_decl = [c for c in decl_internal_cols if c in df.columns]
    available_serie = [c for c in serie_internal_cols if c in df.columns]

    df_declaraciones = (
        df[available_decl]
        .drop_duplicates(subset=["num_formulario"])
        .reset_index(drop=True)
    )

    df_series = df[available_serie].copy().reset_index(drop=True)

    return df_declaraciones, df_series


def process_file(filepath: str, loader: PostgresLoader) -> tuple[int, int]:
    """
    Procesa un único archivo XLSX.
    Retorna (declaraciones_cargadas, series_cargadas).
    """
    archivo_nombre = Path(filepath).name
    logger.info(f"Procesando: {archivo_nombre}")

    try:
        df_raw = pd.read_excel(filepath, engine="openpyxl", dtype=str)
    except Exception as exc:
        logger.error(f"Error leyendo {archivo_nombre}: {exc}")
        return 0, 0

    # Renombrar columnas
    all_cols_map = {**DECLARACION_COLS, **SERIE_COLS}
    df_raw = _rename_columns(df_raw, all_cols_map)

    # Eliminar columnas duplicadas (conservar primera ocurrencia)
    df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()]

    # Separar cabeceras y series
    df_decl_raw, df_series_raw = _split_declaraciones_series(df_raw)
    logger.debug(f"  {len(df_decl_raw)} declaraciones, {len(df_series_raw)} series (raw)")

    # Limpiar
    df_decl_clean = clean_declaraciones(df_decl_raw)
    df_series_clean = clean_series(df_series_raw)

    # Cargar por chunks para controlar uso de memoria y transacciones
    chunk_size = settings.etl_chunk_size
    total_decl = 0
    total_series = 0

    for i in range(0, len(df_decl_clean), chunk_size):
        chunk_decl = df_decl_clean.iloc[i : i + chunk_size]
        formulario_ids = loader.load_declaraciones_batch(chunk_decl, archivo_nombre)

        # Series del mismo rango (aprox): filtrar por num_formulario presentes
        formularios_chunk = set(chunk_decl["num_formulario"].astype(str))
        chunk_series = df_series_clean[
            df_series_clean["num_formulario"].astype(str).isin(formularios_chunk)
        ]
        n_series = loader.load_series_batch(chunk_series, formulario_ids)

        total_decl += len(formulario_ids)
        total_series += n_series
        loader.session.commit()
        logger.debug(f"  Chunk {i//chunk_size + 1}: commit OK")

    logger.success(f"  {archivo_nombre}: {total_decl} decl, {total_series} series cargadas")
    return total_decl, total_series


def run_pipeline(data_dir: str | None = None) -> None:
    """Punto de entrada del pipeline ETL completo."""
    search_dir = data_dir or str(settings.data_dir)
    pattern = str(Path(search_dir) / "**" / "*.xlsx")
    files = sorted(glob.glob(pattern, recursive=True))

    if not files:
        logger.error(f"No se encontraron archivos XLSX en: {pattern}")
        return

    logger.info(f"Archivos encontrados: {len(files)}")

    # Crear esquema si no existe
    create_tables()

    grand_total_decl = 0
    grand_total_series = 0

    with get_db() as session:
        loader = PostgresLoader(session)
        for filepath in files:
            d, s = process_file(filepath, loader)
            grand_total_decl += d
            grand_total_series += s

    logger.success(
        f"ETL completado: {grand_total_decl} declaraciones, {grand_total_series} series"
    )

    # Refrescar vistas analíticas post-carga
    try:
        create_analytical_views()
        refresh_materialized_views()
    except Exception as exc:
        logger.warning(f"No se pudieron refrescar vistas: {exc}")


if __name__ == "__main__":
    import sys
    data_dir_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_pipeline(data_dir_arg)
