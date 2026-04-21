"""
Limpieza y normalización de datos del formulario 600.
"""
import re

import numpy as np
import pandas as pd
from loguru import logger


def clean_declaraciones(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # --- NIT: eliminar todo carácter no numérico ---
    for col in ("nit_exportador", "nit_declarante"):
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace(r"\D", "", regex=True)
                .replace("", np.nan)
            )

    # --- Razón social: strip, upper, normalizar espacios ---
    for col in ("razon_social_exportador", "razon_social_declarante", "razon_social_destinatario"):
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.upper()
                .str.replace(r"\s+", " ", regex=True)
                .replace("NAN", np.nan)
            )

    # --- Valores monetarios: forzar numérico, negativos → NaN ---
    money_cols = [
        "valor_fob_usd", "valor_fletes_usd", "valor_seguros_usd",
        "valor_otros_gastos_usd", "valor_total_exportacion_usd",
        "valor_reintegrar_usd", "valor_agregado_nacional",
        "valor_factura_moneda", "tasa_cambio",
    ]
    for col in money_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df.loc[df[col] < 0, col] = np.nan
            df[col] = df[col].where(df[col].notna(), other=None)

    # --- Fechas: parsear formato YYYYMMDD o timestamp ---
    for col in ("fecha_aceptacion", "fecha_autorizacion_embarque"):
        if col in df.columns:
            df[col] = _parse_date(df[col])

    # --- Pesos / bultos ---
    for col in ("total_peso_bruto_kg", "total_bultos", "total_series"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df.loc[df[col] < 0, col] = np.nan

    # --- Códigos de país: 2 letras upper ---
    for col in ("cod_pais_destino", "cod_pais_tramite"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper().replace("NAN", np.nan)

    # --- Régimen aduanero: numérico ---
    if "regimen_aduanero" in df.columns:
        df["regimen_aduanero"] = pd.to_numeric(df["regimen_aduanero"], errors="coerce")

    # --- Eliminar registros sin NIT exportador (no identificables) ---
    before = len(df)
    df = df.dropna(subset=["nit_exportador"])
    dropped = before - len(df)
    if dropped:
        logger.debug(f"  Dropped {dropped} rows sin NIT exportador")

    return df


def clean_series(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in ("cantidad_fisica", "cantidad_comercial", "peso_bruto_kg",
                "peso_neto_kg", "valor_fob_usd", "num_bultos"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df.loc[df[col] < 0, col] = np.nan

    if "subpartida" in df.columns:
        # Normalizar: eliminar separadores (puntos, guiones) y dejar solo dígitos
        df["subpartida"] = (
            df["subpartida"].astype(str)
            .str.replace(r"\D", "", regex=True)
            .replace("", np.nan)
        )

    for col in ("descripcion", "marcas"):
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.strip()
                .str[:500]  # truncar textos muy largos
                .replace("NAN", np.nan)
            )

    return df


def _parse_date(series: pd.Series) -> pd.Series:
    """
    Parsea fechas en formato YYYYMMDD (int/str) o datetime.
    Retorna pd.Series de tipo datetime64[ns].
    """
    def _try_parse(val):
        if pd.isna(val):
            return pd.NaT
        s = str(int(val)) if isinstance(val, float) else str(val)
        s = re.sub(r"\D", "", s)[:8]
        if len(s) == 8:
            try:
                return pd.to_datetime(s, format="%Y%m%d")
            except ValueError:
                return pd.NaT
        return pd.NaT

    # Primero intentar conversión vectorizada rápida
    try:
        cleaned = series.astype(str).str.extract(r"(\d{8})")[0]
        result = pd.to_datetime(cleaned, format="%Y%m%d", errors="coerce")
        if result.notna().sum() / max(len(result), 1) > 0.5:
            return result
    except Exception:
        pass

    return series.apply(_try_parse)
