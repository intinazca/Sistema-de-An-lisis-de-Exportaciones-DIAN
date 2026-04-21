from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api import queries
from src.api.schemas import (
    DeclaracionResumen,
    EmpresaTop,
    MetricasGlobales,
    PagedResponse,
    TendenciaMensual,
)
from src.db.session import get_db_dependency

router = APIRouter(prefix="/api/v1", tags=["exportaciones"])


@router.get("/metricas", response_model=MetricasGlobales, summary="KPIs globales del dataset")
def metricas_globales(db: Session = Depends(get_db_dependency)):
    return queries.get_metricas_globales(db)


@router.get(
    "/empresas/top",
    response_model=list[EmpresaTop],
    summary="Top N empresas por FOB exportado",
)
def top_empresas(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db_dependency),
):
    return queries.get_top_empresas(db, limit=limit)


@router.get(
    "/tendencia/mensual",
    response_model=list[TendenciaMensual],
    summary="Tendencia mensual de exportaciones",
)
def tendencia_mensual(
    pais_destino: Optional[str] = Query(default=None, description="Código ISO 2 del país"),
    modo_transporte: Optional[str] = Query(default=None),
    db: Session = Depends(get_db_dependency),
):
    return queries.get_tendencia_mensual(db, pais_destino, modo_transporte)


@router.get(
    "/declaraciones",
    response_model=PagedResponse,
    summary="Consulta paginada de declaraciones",
)
def listar_declaraciones(
    nit: Optional[str] = Query(default=None, description="NIT del exportador"),
    pais: Optional[str] = Query(default=None, description="Código ISO 2 del país destino"),
    fecha_desde: Optional[date] = Query(default=None),
    fecha_hasta: Optional[date] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db_dependency),
):
    offset = (page - 1) * page_size
    data, total = queries.get_declaraciones_paginadas(
        db, nit=nit, pais=pais,
        fecha_desde=fecha_desde, fecha_hasta=fecha_hasta,
        offset=offset, limit=page_size,
    )
    return PagedResponse(total=total, page=page, page_size=page_size, data=data)


@router.get(
    "/analisis/paises",
    summary="Distribución de exportaciones por país destino",
)
def distribucion_paises(
    top_n: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db_dependency),
):
    return queries.get_distribucion_paises(db, top_n=top_n)


@router.get(
    "/analisis/subpartidas",
    summary="Top subpartidas arancelarias por FOB",
)
def distribucion_subpartidas(
    top_n: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db_dependency),
):
    return queries.get_distribucion_subpartidas(db, top_n=top_n)
