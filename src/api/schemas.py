from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=500)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class EmpresaTop(BaseModel):
    nit: str
    razon_social: Optional[str]
    total_declaraciones: int
    total_series: int
    fob_total_usd: Optional[float]
    peso_total_kg: Optional[float]
    paises_destino: int
    primera_exportacion: Optional[date]
    ultima_exportacion: Optional[date]

    model_config = {"from_attributes": True}


class TendenciaMensual(BaseModel):
    mes: date
    cod_pais_destino: Optional[str]
    pais_destino: Optional[str]
    modo_transporte: Optional[str]
    declaraciones: int
    fob_usd: Optional[float]
    peso_kg: Optional[float]
    fob_promedio: Optional[float]

    model_config = {"from_attributes": True}


class MetricasGlobales(BaseModel):
    total_declaraciones: int
    total_empresas: int
    total_paises_destino: int
    fob_total_usd: float
    peso_total_kg: float
    periodo_inicio: Optional[date] = None
    periodo_fin: Optional[date] = None


class DeclaracionResumen(BaseModel):
    id: int
    num_formulario: str
    nit_exportador: str
    razon_social_exportador: Optional[str]
    pais_destino: Optional[str]
    valor_fob_usd: Optional[float]
    total_peso_bruto_kg: Optional[float]
    fecha_aceptacion: Optional[date]
    modo_transporte: Optional[str]
    incoterms: Optional[str]

    model_config = {"from_attributes": True}


class PagedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    data: list


class PrediccionFOB(BaseModel):
    nit_exportador: str
    mes_prediccion: str  # YYYY-MM
    fob_predicho_usd: float
    intervalo_inferior: float
    intervalo_superior: float
    confianza: float
