"""
Análisis exploratorio de las 10 empresas top.
Ejecutar directamente: python -m src.etl.exploratory_analysis
"""
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


def load_all_data(data_dir: str = "../") -> pd.DataFrame:
    import glob
    from pathlib import Path
    from src.etl.column_map import DECLARACION_COLS
    from src.etl.cleaner import clean_declaraciones

    files = sorted(glob.glob(str(Path(data_dir) / "**" / "*.xlsx"), recursive=True))
    dfs = []
    for f in files:
        print(f"  Cargando {Path(f).name}...", flush=True)
        df = pd.read_excel(f, engine="openpyxl", dtype=str)
        existing = {k: v for k, v in DECLARACION_COLS.items() if k in df.columns}
        df = df.rename(columns=existing)
        df = df[list(existing.values())].drop_duplicates(subset=["num_formulario"])
        df = clean_declaraciones(df)
        dfs.append(df)

    return pd.concat(dfs, ignore_index=True)


def analyze_top_companies(df: pd.DataFrame, top_n: int = 10) -> None:
    print("\n" + "="*70)
    print("ANÁLISIS: TOP 10 EMPRESAS EXPORTADORAS (Oct-Dic 2025)")
    print("="*70)

    # Convertir tipos
    df["valor_fob_usd"] = pd.to_numeric(df["valor_fob_usd"], errors="coerce")
    df["total_peso_bruto_kg"] = pd.to_numeric(df["total_peso_bruto_kg"], errors="coerce")
    df["fecha_aceptacion"] = pd.to_datetime(df["fecha_aceptacion"], errors="coerce")

    # Ranking por FOB
    ranking = (
        df.groupby(["nit_exportador", "razon_social_exportador"])
        .agg(
            declaraciones=("num_formulario", "nunique"),
            fob_total=("valor_fob_usd", "sum"),
            fob_promedio=("valor_fob_usd", "mean"),
            peso_total_ton=("total_peso_bruto_kg", lambda x: x.sum() / 1000),
            paises_destino=("cod_pais_destino", "nunique"),
        )
        .sort_values("fob_total", ascending=False)
        .head(top_n)
        .reset_index()
    )

    fob_universo = df["valor_fob_usd"].sum()
    ranking["participacion_pct"] = (ranking["fob_total"] / fob_universo * 100).round(2)
    ranking["fob_total_M"] = (ranking["fob_total"] / 1e6).round(3)

    print("\n📊 Ranking por FOB Total Exportado:")
    print(ranking[[
        "nit_exportador", "razon_social_exportador", "declaraciones",
        "fob_total_M", "participacion_pct", "paises_destino", "peso_total_ton"
    ]].to_string(index=False))

    # Concentración
    top10_share = ranking["participacion_pct"].sum()
    print(f"\n⚠️  CONCENTRACIÓN: Top 10 empresas = {top10_share:.1f}% del FOB total")
    print(f"   FOB universo total: ${fob_universo:,.0f} USD")

    # Tendencia mensual por empresa top
    print("\n📈 Tendencia Mensual (Top 5):")
    top5_nits = ranking["nit_exportador"].head(5).tolist()
    df_top5 = df[df["nit_exportador"].isin(top5_nits)].copy()
    df_top5["mes"] = df_top5["fecha_aceptacion"].dt.to_period("M")

    tendencia = (
        df_top5.groupby(["mes", "nit_exportador", "razon_social_exportador"])["valor_fob_usd"]
        .sum()
        .reset_index()
        .sort_values(["nit_exportador", "mes"])
    )
    print(tendencia.to_string(index=False))

    # Distribución por modo transporte
    print("\n🚚 Modo de Transporte (Top 10 empresas):")
    df_top10 = df[df["nit_exportador"].isin(ranking["nit_exportador"].tolist())]
    modo_dist = (
        df_top10.groupby("modo_transporte")["valor_fob_usd"]
        .sum()
        .sort_values(ascending=False)
    )
    for modo, fob in modo_dist.items():
        print(f"  {modo:<35} ${fob:>15,.0f}")

    # Destinos principales
    print("\n🌍 Países Destino más frecuentes (Top 10 empresas):")
    dest = (
        df_top10.groupby(["pais_destino", "cod_pais_destino"])["valor_fob_usd"]
        .sum()
        .sort_values(ascending=False)
        .head(15)
    )
    for (pais, cod), fob in dest.items():
        print(f"  [{cod}] {pais:<30} ${fob:>15,.0f}")

    # Insights
    print("\n💡 INSIGHTS DE NEGOCIO:")
    print(f"  1. Las {top_n} mayores empresas concentran el {top10_share:.1f}% del FOB — "
          f"mercado {'altamente concentrado' if top10_share > 30 else 'medianamente diversificado'}.")

    modo_principal = modo_dist.index[0] if len(modo_dist) > 0 else "N/A"
    print(f"  2. Modo de transporte dominante: {modo_principal}")

    if len(tendencia) > 0:
        variacion = tendencia.groupby("nit_exportador")["valor_fob_usd"].pct_change().mean()
        print(f"  3. Variación promedio mensual: {variacion * 100:+.1f}%")


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "../"
    print(f"Cargando datos desde: {data_dir}")
    df = load_all_data(data_dir)
    print(f"Total declaraciones únicas: {len(df):,}")
    analyze_top_companies(df)
