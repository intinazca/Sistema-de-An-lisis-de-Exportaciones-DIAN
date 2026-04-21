"""
Modelo Relacional - Exportaciones DIAN Formulario 600
=====================================================

Diagrama lógico:
  dim_empresas (1) ──── (N) declaraciones (1) ──── (N) series

- dim_empresas: catálogo de exportadores (deduplicado por NIT)
- declaraciones: una por formulario DEX (nivel cabecera)
- series: ítems de producto dentro de cada declaración
"""
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class DimEmpresa(Base):
    """Dimensión empresas exportadoras — deduplicada por NIT."""

    __tablename__ = "dim_empresas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nit = Column(String(20), nullable=False, unique=True)
    razon_social = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    declaraciones = relationship("Declaracion", back_populates="empresa")


class Declaracion(Base):
    """
    Cabecera de la declaración de exportación (DEX).
    Granularidad: un registro por número de formulario único.
    """

    __tablename__ = "declaraciones"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    num_formulario = Column(String(30), nullable=False)
    anio = Column(SmallInteger)
    empresa_id = Column(Integer, ForeignKey("dim_empresas.id"), nullable=False)

    # Declarante / agencia de aduanas
    nit_declarante = Column(String(20))
    razon_social_declarante = Column(Text)

    # Destinatario
    razon_social_destinatario = Column(Text)
    ciudad_destinatario = Column(String(200))

    # Clasificación aduanera
    clase_dua = Column(String(200))
    regimen_aduanero = Column(SmallInteger)
    tipo_despacho = Column(String(200))

    # Geografía
    cod_aduana_despacho = Column(String(300))
    cod_pais_destino = Column(String(5))
    pais_destino = Column(Text)
    lugar_destino = Column(String(300))
    cod_region_procedencia = Column(SmallInteger)

    # Logística
    modo_transporte = Column(String(200))
    tipo_carga = Column(String(200))
    incoterms = Column(String(10))
    lugar_entrega = Column(String(300))

    # Valores monetarios (USD)
    moneda_transaccion = Column(SmallInteger)
    valor_factura_moneda = Column(Float)
    tasa_cambio = Column(Float)
    valor_fob_usd = Column(Float)
    valor_fletes_usd = Column(Float)
    valor_seguros_usd = Column(Float)
    valor_otros_gastos_usd = Column(Float)
    valor_total_exportacion_usd = Column(Float)
    valor_reintegrar_usd = Column(Float)
    valor_agregado_nacional = Column(Float)

    # Totales físicos
    total_series = Column(SmallInteger)
    total_bultos = Column(Integer)
    total_peso_bruto_kg = Column(Float)

    # Fechas
    fecha_aceptacion = Column(Date)
    fecha_autorizacion_embarque = Column(Date)

    # Auditoría ETL
    archivo_fuente = Column(String(100))
    cargado_en = Column(DateTime, server_default=func.now())

    empresa = relationship("DimEmpresa", back_populates="declaraciones")
    series = relationship("Serie", back_populates="declaracion")

    __table_args__ = (
        UniqueConstraint("num_formulario", name="uq_declaraciones_formulario"),
        Index("ix_declaraciones_empresa_fecha", "empresa_id", "fecha_aceptacion"),
        Index("ix_declaraciones_pais_destino", "cod_pais_destino"),
        Index("ix_declaraciones_fecha", "fecha_aceptacion"),
        Index("ix_declaraciones_fob", "valor_fob_usd"),
        Index("ix_declaraciones_aduana", "cod_aduana_despacho"),
    )


class Serie(Base):
    """
    Línea de producto dentro de una declaración.
    Contiene subpartida arancelaria, cantidades, pesos y valor FOB.
    """

    __tablename__ = "series"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    declaracion_id = Column(BigInteger, ForeignKey("declaraciones.id"), nullable=False)

    num_serie = Column(SmallInteger)
    nomenclatura = Column(String(50))
    subpartida = Column(String(20))
    cod_complementario = Column(String(50))

    # Unidades
    cod_unidad_fisica = Column(String(200))
    cantidad_fisica = Column(Float)
    cod_unidad_comercial = Column(String(200))
    cantidad_comercial = Column(Float)

    # Embalaje / peso
    cod_clase_embalaje = Column(String(200))
    num_bultos = Column(Integer)
    peso_bruto_kg = Column(Float)
    peso_neto_kg = Column(Float)

    # Valor
    valor_fob_usd = Column(Float)

    # Descripción
    marcas = Column(Text)
    descripcion = Column(Text)

    # Origen
    cod_pais_origen = Column(String(100))
    cod_region_origen = Column(SmallInteger)

    declaracion = relationship("Declaracion", back_populates="series")

    __table_args__ = (
        Index("ix_series_declaracion", "declaracion_id"),
        Index("ix_series_subpartida", "subpartida"),
        Index("ix_series_fob", "valor_fob_usd"),
    )
