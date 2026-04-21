"""Tests del módulo de limpieza ETL."""
import numpy as np
import pandas as pd
import pytest

from src.etl.cleaner import clean_declaraciones, clean_series


@pytest.fixture
def sample_declaraciones():
    return pd.DataFrame({
        "nit_exportador": ["860503159", "901587729", np.nan, "123-456", "INVALID"],
        "razon_social_exportador": ["empresa a SAS", None, "empresa c", "empresa D", "empresa e"],
        "valor_fob_usd": ["1500.5", "-200", "abc", "0", "999999"],
        "fecha_aceptacion": ["20251009", "20251109", "invalid", "20251209", np.nan],
        "cod_pais_destino": ["ec", "FR", "us", None, "GT"],
        "regimen_aduanero": ["42", "42", None, "abc", "42"],
        "total_peso_bruto_kg": ["51.6", "-10", None, "100", "200"],
    })


def test_nit_limpieza(sample_declaraciones):
    result = clean_declaraciones(sample_declaraciones.dropna(subset=["nit_exportador"]).iloc[:2])
    # Solo dígitos
    assert result["nit_exportador"].iloc[0] == "860503159"
    assert result["nit_exportador"].iloc[1] == "901587729"


def test_nit_con_guion():
    df = pd.DataFrame({"nit_exportador": ["123-456"], "razon_social_exportador": ["X"]})
    result = clean_declaraciones(df)
    assert result["nit_exportador"].iloc[0] == "123456"


def test_valores_negativos_a_nan(sample_declaraciones):
    # -200 debe convertirse a NaN
    df = sample_declaraciones.dropna(subset=["nit_exportador"]).copy()
    df = df[df["nit_exportador"] != "INVALID"]
    result = clean_declaraciones(df)
    neg_rows = result[result["valor_fob_usd"] < 0]
    assert len(neg_rows) == 0


def test_fecha_parsing():
    df = pd.DataFrame({
        "nit_exportador": ["860503159"],
        "fecha_aceptacion": ["20251009"],
    })
    result = clean_declaraciones(df)
    assert str(result["fecha_aceptacion"].iloc[0].date()) == "2025-10-09"


def test_drop_sin_nit(sample_declaraciones):
    result = clean_declaraciones(sample_declaraciones)
    # La fila con nit_exportador=NaN debe eliminarse
    assert result["nit_exportador"].isna().sum() == 0


def test_razon_social_upper():
    df = pd.DataFrame({
        "nit_exportador": ["123"],
        "razon_social_exportador": ["empresa a   sas"],
    })
    result = clean_declaraciones(df)
    assert result["razon_social_exportador"].iloc[0] == "EMPRESA A SAS"


def test_clean_series_negativos():
    df = pd.DataFrame({
        "num_formulario": ["001", "002"],
        "valor_fob_usd": ["-500", "1500.5"],
        "peso_bruto_kg": ["100", "-50"],
        "subpartida": ["3926909090", "1804002000"],
    })
    result = clean_series(df)
    assert pd.isna(result["valor_fob_usd"].iloc[0])
    assert pd.isna(result["peso_bruto_kg"].iloc[1])


def test_clean_series_subpartida():
    df = pd.DataFrame({
        "num_formulario": ["001"],
        "subpartida": ["3926.90.90.90"],
        "valor_fob_usd": ["100"],
    })
    result = clean_series(df)
    assert result["subpartida"].iloc[0] == "3926909090"
