"""Crea todas las tablas y vistas analíticas."""
from loguru import logger
from sqlalchemy import text

from src.db.models import Base
from src.db.session import engine


def create_tables() -> None:
    logger.info("Creando esquema de base de datos...")
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    logger.success("Tablas creadas exitosamente.")


def create_analytical_views() -> None:
    """Vistas materializadas para acelerar queries analíticos frecuentes."""
    views_sql = [
        """
        DROP MATERIALIZED VIEW IF EXISTS mv_empresas_top CASCADE;
        """,
        """
        CREATE MATERIALIZED VIEW mv_empresas_top AS
        SELECT
            e.nit,
            e.razon_social,
            COUNT(DISTINCT d.id)                          AS total_declaraciones,
            COUNT(s.id)                                   AS total_series,
            COALESCE(SUM(d.valor_fob_usd) FILTER (WHERE d.valor_fob_usd::text != 'NaN'), 0) AS fob_total_usd,
            SUM(d.total_peso_bruto_kg)                    AS peso_total_kg,
            COUNT(DISTINCT d.cod_pais_destino)            AS paises_destino,
            MIN(d.fecha_aceptacion)                       AS primera_exportacion,
            MAX(d.fecha_aceptacion)                       AS ultima_exportacion
        FROM dim_empresas e
        JOIN declaraciones d ON d.empresa_id = e.id
        LEFT JOIN series s ON s.declaracion_id = d.id
        WHERE d.valor_fob_usd IS NOT NULL
          AND d.valor_fob_usd::text != 'NaN'
        GROUP BY e.nit, e.razon_social
        WITH DATA;
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uix_mv_empresas_top_nit
            ON mv_empresas_top (nit);
        """,
        """
        DROP MATERIALIZED VIEW IF EXISTS mv_tendencia_mensual CASCADE;
        """,
        """
        CREATE MATERIALIZED VIEW mv_tendencia_mensual AS
        SELECT
            DATE_TRUNC('month', d.fecha_aceptacion)::date AS mes,
            d.cod_pais_destino,
            d.pais_destino,
            d.modo_transporte,
            COUNT(DISTINCT d.id)                          AS declaraciones,
            COALESCE(SUM(d.valor_fob_usd) FILTER (WHERE d.valor_fob_usd::text != 'NaN'), 0) AS fob_usd,
            SUM(d.total_peso_bruto_kg)                    AS peso_kg,
            AVG(d.valor_fob_usd) FILTER (WHERE d.valor_fob_usd::text != 'NaN')              AS fob_promedio
        FROM declaraciones d
        WHERE d.fecha_aceptacion IS NOT NULL
          AND d.valor_fob_usd IS NOT NULL
          AND d.valor_fob_usd::text != 'NaN'
        GROUP BY 1, 2, 3, 4
        WITH DATA;
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_mv_tendencia_mes
            ON mv_tendencia_mensual (mes);
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uix_mv_tendencia_mes_pais_modo
            ON mv_tendencia_mensual (mes, cod_pais_destino, modo_transporte);
        """,
    ]

    with engine.connect() as conn:
        for sql in views_sql:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception as exc:
                logger.warning(f"Vista/índice ya existe o error: {exc}")

    logger.success("Vistas analíticas creadas.")


def refresh_materialized_views() -> None:
    with engine.connect() as conn:
        for view in ("mv_empresas_top", "mv_tendencia_mensual"):
            conn.execute(text(f"REFRESH MATERIALIZED VIEW {view}"))
            conn.commit()
    logger.info("Vistas materializadas actualizadas.")


if __name__ == "__main__":
    create_tables()
    create_analytical_views()
