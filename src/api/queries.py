"""
Queries analíticos — centralizados aquí para no mezclar SQL con routing.
"""
import math
from datetime import date
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


def _clean(d: dict) -> dict:
    """Reemplaza NaN/Inf por None para que sean JSON-serializables."""
    return {
        k: (None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
        for k, v in d.items()
    }


def get_metricas_globales(db: Session) -> dict:
    sql = text("""
        SELECT
            COUNT(DISTINCT d.id)                 AS total_declaraciones,
            COUNT(DISTINCT d.empresa_id)          AS total_empresas,
            COUNT(DISTINCT d.cod_pais_destino)    AS total_paises_destino,
            COALESCE(SUM(d.valor_fob_usd) FILTER (WHERE d.valor_fob_usd IS NOT NULL AND d.valor_fob_usd::text != 'NaN'), 0) AS fob_total_usd,
            COALESCE(SUM(d.total_peso_bruto_kg) FILTER (WHERE d.total_peso_bruto_kg IS NOT NULL AND d.total_peso_bruto_kg::text != 'NaN'), 0) AS peso_total_kg,
            MIN(d.fecha_aceptacion)               AS periodo_inicio,
            MAX(d.fecha_aceptacion)               AS periodo_fin
        FROM declaraciones d
    """)
    row = db.execute(sql).mappings().one()
    return _clean(dict(row))


def get_top_empresas(db: Session, limit: int = 10) -> list[dict]:
    sql = text("""
        SELECT
            nit, razon_social, total_declaraciones, total_series,
            fob_total_usd, peso_total_kg, paises_destino,
            primera_exportacion, ultima_exportacion
        FROM mv_empresas_top
        ORDER BY fob_total_usd DESC
        LIMIT :limit
    """)
    rows = db.execute(sql, {"limit": limit}).mappings().all()
    return [_clean(dict(r)) for r in rows]


def get_tendencia_mensual(
    db: Session,
    pais_destino: Optional[str] = None,
    modo_transporte: Optional[str] = None,
) -> list[dict]:
    where_clauses = []
    params: dict = {}

    if pais_destino:
        where_clauses.append(
            "(cod_pais_destino ILIKE :pais OR pais_destino ILIKE :pais_nombre)"
        )
        params["pais"] = pais_destino.upper()
        params["pais_nombre"] = f"%{pais_destino}%"
    if modo_transporte:
        where_clauses.append("unaccent(modo_transporte) ILIKE unaccent(:modo)")
        params["modo"] = f"%{modo_transporte}%"

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    sql = text(f"""
        SELECT mes, cod_pais_destino, pais_destino, modo_transporte,
               declaraciones, fob_usd, peso_kg, fob_promedio
        FROM mv_tendencia_mensual
        {where_sql}
        ORDER BY mes ASC
    """)
    rows = db.execute(sql, params).mappings().all()
    return [_clean(dict(r)) for r in rows]


def get_declaraciones_paginadas(
    db: Session,
    nit: Optional[str] = None,
    pais: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[dict], int]:
    where_clauses = ["1=1"]
    params: dict = {"offset": offset, "limit": limit}

    if nit:
        where_clauses.append("e.nit = :nit")
        params["nit"] = nit
    if pais:
        where_clauses.append(
            "(d.cod_pais_destino ILIKE :pais OR d.pais_destino ILIKE :pais_nombre)"
        )
        params["pais"] = pais.upper()
        params["pais_nombre"] = f"%{pais}%"
    if fecha_desde:
        where_clauses.append("d.fecha_aceptacion >= :f_desde")
        params["f_desde"] = fecha_desde
    if fecha_hasta:
        where_clauses.append("d.fecha_aceptacion <= :f_hasta")
        params["f_hasta"] = fecha_hasta

    where_sql = " AND ".join(where_clauses)

    count_sql = text(f"""
        SELECT COUNT(*) FROM declaraciones d
        JOIN dim_empresas e ON e.id = d.empresa_id
        WHERE {where_sql}
    """)
    total = db.execute(count_sql, params).scalar()

    data_sql = text(f"""
        SELECT
            d.id, d.num_formulario, e.nit AS nit_exportador,
            e.razon_social AS razon_social_exportador,
            d.pais_destino, d.valor_fob_usd, d.total_peso_bruto_kg,
            d.fecha_aceptacion, d.modo_transporte, d.incoterms
        FROM declaraciones d
        JOIN dim_empresas e ON e.id = d.empresa_id
        WHERE {where_sql}
        ORDER BY d.fecha_aceptacion DESC
        LIMIT :limit OFFSET :offset
    """)
    rows = db.execute(data_sql, params).mappings().all()
    return [_clean(dict(r)) for r in rows], total


def get_distribucion_paises(db: Session, top_n: int = 20) -> list[dict]:
    sql = text("""
        SELECT
            cod_pais_destino,
            pais_destino,
            COUNT(*)         AS declaraciones,
            COALESCE(SUM(valor_fob_usd) FILTER (WHERE valor_fob_usd::text != 'NaN'), 0) AS fob_usd
        FROM declaraciones
        WHERE cod_pais_destino IS NOT NULL
          AND valor_fob_usd IS NOT NULL
        GROUP BY cod_pais_destino, pais_destino
        ORDER BY fob_usd DESC
        LIMIT :n
    """)
    rows = db.execute(sql, {"n": top_n}).mappings().all()
    return [_clean(dict(r)) for r in rows]


def get_distribucion_subpartidas(db: Session, top_n: int = 20) -> list[dict]:
    sql = text("""
        SELECT
            s.subpartida,
            TRIM(SPLIT_PART(
                SPLIT_PART(
                    (SELECT descripcion FROM series s2
                     WHERE s2.subpartida = s.subpartida AND s2.descripcion IS NOT NULL
                     GROUP BY descripcion ORDER BY COUNT(*) DESC LIMIT 1),
                    ':', 2
                ), ',', 1
            )) AS descripcion_corta,
            COUNT(*)             AS lineas,
            SUM(s.valor_fob_usd) AS fob_usd,
            SUM(s.peso_bruto_kg) AS peso_kg
        FROM series s
        WHERE s.subpartida IS NOT NULL
          AND s.valor_fob_usd IS NOT NULL
        GROUP BY s.subpartida
        ORDER BY fob_usd DESC
        LIMIT :n
    """)
    rows = db.execute(sql, {"n": top_n}).mappings().all()
    return [_clean(dict(r)) for r in rows]
