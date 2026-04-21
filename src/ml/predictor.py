"""
Modelo ML: Predicción de valor FOB mensual por empresa exportadora.

Justificación del modelo:
- Objetivo: predecir el FOB total que una empresa exportará en el siguiente mes
- Algoritmo: Random Forest Regressor
  * Robusto ante outliers (distribución FOB es muy asimétrica, hay empresas con
    exportaciones millonarias junto a pequeños exportadores)
  * Captura interacciones no lineales (país destino × modo transporte × mes)
  * No requiere normalización de features
  * Permite feature importance interpretable para el negocio

Variables (features):
  - mes_numero (1-12): estacionalidad
  - anio: tendencia temporal
  - num_declaraciones_mes_anterior: proxy de actividad reciente
  - fob_mes_anterior: valor FOB último mes (lag-1)
  - fob_media_3m: promedio 3 meses anteriores (rolling window)
  - pct_cambio_fob: variación porcentual respecto al mes anterior
  - num_paises_distintos: diversificación de destinos
  - modo_transporte_aereo (0/1): feature binaria
  - modo_transporte_maritimo (0/1)
  - region_procedencia: código numérico

Target: fob_mes_actual (en USD, transformado con log1p para normalizar distribución)
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.config import settings


def build_features_from_db(db_session) -> pd.DataFrame:
    """
    Construye el dataset de features a partir de la base de datos.
    Granularidad: empresa × mes.
    """
    from sqlalchemy import text

    sql = text("""
        SELECT
            e.nit,
            DATE_TRUNC('month', d.fecha_aceptacion)::date  AS mes,
            COUNT(DISTINCT d.id)                           AS num_declaraciones,
            SUM(d.valor_fob_usd)                           AS fob_total,
            COUNT(DISTINCT d.cod_pais_destino)             AS num_paises,
            AVG(d.total_peso_bruto_kg)                     AS peso_promedio,
            MODE() WITHIN GROUP (ORDER BY d.modo_transporte) AS modo_principal,
            MODE() WITHIN GROUP (ORDER BY d.cod_region_procedencia::text) AS region_principal
        FROM declaraciones d
        JOIN dim_empresas e ON e.id = d.empresa_id
        WHERE d.fecha_aceptacion IS NOT NULL
          AND d.valor_fob_usd > 0
        GROUP BY e.nit, DATE_TRUNC('month', d.fecha_aceptacion)
        ORDER BY e.nit, mes
    """)

    rows = db_session.execute(sql).mappings().all()
    df = pd.DataFrame([dict(r) for r in rows])
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Feature engineering temporal por empresa.
    Requiere columnas: nit, mes, fob_total, num_declaraciones, num_paises.
    """
    df = df.copy()
    df["mes"] = pd.to_datetime(df["mes"])
    df = df.sort_values(["nit", "mes"]).reset_index(drop=True)

    # Features temporales
    df["mes_numero"] = df["mes"].dt.month
    df["anio"] = df["mes"].dt.year
    df["trimestre"] = df["mes"].dt.quarter

    # Lags y rolling por empresa (TimeSeriesCV requiere no data leakage)
    df["fob_lag1"] = df.groupby("nit")["fob_total"].shift(1)
    df["fob_lag2"] = df.groupby("nit")["fob_total"].shift(2)
    df["fob_lag3"] = df.groupby("nit")["fob_total"].shift(3)
    df["fob_rolling3"] = (
        df.groupby("nit")["fob_total"]
        .transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
    )
    df["decl_lag1"] = df.groupby("nit")["num_declaraciones"].shift(1)

    # Variación porcentual (clip para evitar infinitos)
    df["pct_cambio_fob"] = (
        (df["fob_total"] - df["fob_lag1"]) / (df["fob_lag1"] + 1)
    ).clip(-5, 5)

    # Encoding modo transporte
    df["es_aereo"] = df["modo_principal"].str.contains("éreo|Aereo|aereo", na=False).astype(int)
    df["es_maritimo"] = df["modo_principal"].str.contains("arítimo|Maritimo", na=False).astype(int)
    df["es_carretero"] = df["modo_principal"].str.contains("arretero|carretero", na=False).astype(int)

    # Target: log1p para normalizar distribución asimétrica
    df["target"] = np.log1p(df["fob_total"])

    return df


FEATURE_COLS = [
    "mes_numero", "trimestre", "anio",
    "fob_lag1", "fob_lag2", "fob_lag3", "fob_rolling3",
    "decl_lag1", "pct_cambio_fob",
    "num_paises", "peso_promedio",
    "es_aereo", "es_maritimo", "es_carretero",
]


def train_model(df: pd.DataFrame) -> tuple[Pipeline, dict]:
    """
    Entrena el modelo usando TimeSeriesSplit para respetar la naturaleza temporal.
    Retorna (pipeline_entrenado, metricas).
    """
    df_feat = engineer_features(df)
    df_feat = df_feat.dropna(subset=FEATURE_COLS + ["target"])

    X = df_feat[FEATURE_COLS].values
    y = df_feat["target"].values

    # TimeSeriesSplit: nunca usa datos futuros para entrenar
    tscv = TimeSeriesSplit(n_splits=3)

    mae_scores, rmse_scores, r2_scores = [], [], []

    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("rf", RandomForestRegressor(
                n_estimators=200,
                max_depth=12,
                min_samples_leaf=5,
                n_jobs=-1,
                random_state=42,
            )),
        ])
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)

        # Métricas en escala original (revertir log1p)
        y_test_orig = np.expm1(y_test)
        y_pred_orig = np.expm1(y_pred)

        mae_scores.append(mean_absolute_error(y_test_orig, y_pred_orig))
        rmse_scores.append(np.sqrt(mean_squared_error(y_test_orig, y_pred_orig)))
        r2_scores.append(r2_score(y_test, y_pred))  # R² en escala log
        logger.info(
            f"Fold {fold+1}: MAE=${mae_scores[-1]:,.0f} "
            f"RMSE=${rmse_scores[-1]:,.0f} R²={r2_scores[-1]:.3f}"
        )

    # Entrenar modelo final con todos los datos
    final_pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("rf", RandomForestRegressor(
            n_estimators=300,
            max_depth=12,
            min_samples_leaf=5,
            n_jobs=-1,
            random_state=42,
        )),
    ])
    final_pipe.fit(X, y)

    metrics = {
        "mae_promedio": float(np.mean(mae_scores)),
        "rmse_promedio": float(np.mean(rmse_scores)),
        "r2_promedio": float(np.mean(r2_scores)),
        "n_samples": len(df_feat),
        "features": FEATURE_COLS,
    }

    # Feature importance
    rf = final_pipe.named_steps["rf"]
    importance = dict(zip(FEATURE_COLS, rf.feature_importances_))
    metrics["feature_importance"] = importance

    logger.info(f"Modelo final - MAE=${metrics['mae_promedio']:,.0f} R²={metrics['r2_promedio']:.3f}")
    return final_pipe, metrics


def save_model(pipeline: Pipeline, metrics: dict, model_dir: str | None = None) -> Path:
    out_dir = Path(model_dir or settings.ml_models_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = out_dir / "fob_predictor.joblib"
    metrics_path = out_dir / "fob_predictor_metrics.json"

    joblib.dump(pipeline, model_path)
    import json
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2, default=str)

    logger.success(f"Modelo guardado en {model_path}")
    return model_path


def load_model(model_dir: str | None = None) -> Pipeline:
    model_path = Path(model_dir or settings.ml_models_dir) / "fob_predictor.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"Modelo no encontrado en {model_path}. Ejecuta train primero.")
    return joblib.load(model_path)


def predict_next_month(
    pipeline: Pipeline,
    empresa_df: pd.DataFrame,
) -> dict:
    """
    Predice el FOB del próximo mes para una empresa dado su historial.
    empresa_df debe tener las columnas base (mes, fob_total, num_declaraciones, etc.)
    """
    df_feat = engineer_features(empresa_df)
    last_row = df_feat.dropna(subset=["fob_lag1"]).iloc[-1:]

    if last_row.empty:
        raise ValueError("Historial insuficiente para predecir (mínimo 2 meses)")

    X = last_row[FEATURE_COLS].values
    y_log_pred = pipeline.predict(X)[0]
    y_pred = float(np.expm1(y_log_pred))

    # Intervalo de confianza usando desviación estándar de árboles
    rf = pipeline.named_steps["rf"]
    scaler = pipeline.named_steps["scaler"]
    X_scaled = scaler.transform(X)
    tree_preds = np.array([t.predict(X_scaled)[0] for t in rf.estimators_])
    std = np.std(np.expm1(tree_preds))

    return {
        "fob_predicho_usd": round(y_pred, 2),
        "intervalo_inferior": round(max(0, y_pred - 1.96 * std), 2),
        "intervalo_superior": round(y_pred + 1.96 * std, 2),
        "confianza": 0.95,
    }


def run_training_pipeline(db_session) -> dict:
    """Orquesta todo el flujo de entrenamiento."""
    logger.info("Construyendo features desde BD...")
    df = build_features_from_db(db_session)
    logger.info(f"Dataset: {len(df)} empresa-mes combinaciones")

    pipeline, metrics = train_model(df)
    save_model(pipeline, metrics)
    return metrics
