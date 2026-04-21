"""
Carga de datos a PostgreSQL.
Estrategia: upsert por num_formulario para idempotencia.
"""
import pandas as pd
from loguru import logger
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.db.models import Declaracion, DimEmpresa, Serie


class PostgresLoader:
    def __init__(self, session: Session):
        self.session = session
        self._empresa_cache: dict[str, int] = {}  # nit → id

    def upsert_empresa(self, nit: str, razon_social: str | None) -> int:
        if nit in self._empresa_cache:
            return self._empresa_cache[nit]

        empresa = self.session.query(DimEmpresa).filter_by(nit=nit).first()
        if not empresa:
            empresa = DimEmpresa(nit=nit, razon_social=razon_social)
            self.session.add(empresa)
            self.session.flush()  # obtener id sin commit
        elif razon_social and not empresa.razon_social:
            empresa.razon_social = razon_social

        self._empresa_cache[nit] = empresa.id
        return empresa.id

    def load_declaraciones_batch(
        self, df_declaraciones: pd.DataFrame, archivo_fuente: str
    ) -> dict[str, int]:
        """
        Inserta declaraciones. Retorna dict num_formulario → id.
        Omite duplicados (upsert por num_formulario).
        """
        formulario_id_map: dict[str, int] = {}
        nuevas = 0
        omitidas = 0

        for _, row in df_declaraciones.iterrows():
            num_form = str(row["num_formulario"])
            nit = str(row["nit_exportador"])

            # Verificar si ya existe
            existing = (
                self.session.query(Declaracion)
                .filter_by(num_formulario=num_form)
                .first()
            )
            if existing:
                formulario_id_map[num_form] = existing.id
                omitidas += 1
                continue

            empresa_id = self.upsert_empresa(nit, row.get("razon_social_exportador"))

            decl = Declaracion(
                num_formulario=num_form,
                anio=_safe_int(row.get("anio")),
                empresa_id=empresa_id,
                nit_declarante=row.get("nit_declarante"),
                razon_social_declarante=row.get("razon_social_declarante"),
                razon_social_destinatario=row.get("razon_social_destinatario"),
                ciudad_destinatario=row.get("ciudad_destinatario"),
                clase_dua=row.get("clase_dua"),
                regimen_aduanero=_safe_int(row.get("regimen_aduanero")),
                tipo_despacho=row.get("tipo_despacho"),
                cod_aduana_despacho=row.get("cod_aduana_despacho"),
                cod_pais_destino=row.get("cod_pais_destino"),
                pais_destino=row.get("pais_destino"),
                lugar_destino=row.get("lugar_destino"),
                cod_region_procedencia=_safe_int(row.get("cod_region_procedencia")),
                modo_transporte=row.get("modo_transporte"),
                tipo_carga=row.get("tipo_carga"),
                incoterms=row.get("incoterms"),
                lugar_entrega=row.get("lugar_entrega"),
                moneda_transaccion=_safe_int(row.get("moneda_transaccion")),
                valor_factura_moneda=row.get("valor_factura_moneda"),
                tasa_cambio=row.get("tasa_cambio"),
                valor_fob_usd=row.get("valor_fob_usd"),
                valor_fletes_usd=row.get("valor_fletes_usd"),
                valor_seguros_usd=row.get("valor_seguros_usd"),
                valor_otros_gastos_usd=row.get("valor_otros_gastos_usd"),
                valor_total_exportacion_usd=row.get("valor_total_exportacion_usd"),
                valor_reintegrar_usd=row.get("valor_reintegrar_usd"),
                valor_agregado_nacional=row.get("valor_agregado_nacional"),
                total_series=_safe_int(row.get("total_series")),
                total_bultos=_safe_int(row.get("total_bultos")),
                total_peso_bruto_kg=row.get("total_peso_bruto_kg"),
                fecha_aceptacion=_safe_date(row.get("fecha_aceptacion")),
                fecha_autorizacion_embarque=_safe_date(row.get("fecha_autorizacion_embarque")),
                archivo_fuente=archivo_fuente,
            )
            self.session.add(decl)
            self.session.flush()
            formulario_id_map[num_form] = decl.id
            nuevas += 1

        logger.debug(f"  Declaraciones: {nuevas} nuevas, {omitidas} omitidas")
        return formulario_id_map

    def load_series_batch(
        self, df_series: pd.DataFrame, formulario_id_map: dict[str, int]
    ) -> int:
        """Inserta series asociadas a las declaraciones cargadas."""
        count = 0
        series_objects = []

        for _, row in df_series.iterrows():
            num_form = str(row.get("num_formulario", ""))
            decl_id = formulario_id_map.get(num_form)
            if not decl_id:
                continue

            series_objects.append(
                Serie(
                    declaracion_id=decl_id,
                    num_serie=_safe_int(row.get("num_serie")),
                    nomenclatura=row.get("nomenclatura"),
                    subpartida=row.get("subpartida"),
                    cod_complementario=row.get("cod_complementario"),
                    cod_unidad_fisica=row.get("cod_unidad_fisica"),
                    cantidad_fisica=row.get("cantidad_fisica"),
                    cod_unidad_comercial=row.get("cod_unidad_comercial"),
                    cantidad_comercial=row.get("cantidad_comercial"),
                    cod_clase_embalaje=row.get("cod_clase_embalaje"),
                    num_bultos=_safe_int(row.get("num_bultos")),
                    peso_bruto_kg=row.get("peso_bruto_kg"),
                    peso_neto_kg=row.get("peso_neto_kg"),
                    valor_fob_usd=row.get("valor_fob_usd"),
                    marcas=row.get("marcas"),
                    descripcion=row.get("descripcion"),
                    cod_pais_origen=row.get("cod_pais_origen"),
                    cod_region_origen=_safe_int(row.get("cod_region_origen")),
                )
            )
            count += 1

        if series_objects:
            self.session.bulk_save_objects(series_objects)

        return count


def _safe_int(val) -> int | None:
    try:
        return int(val) if pd.notna(val) else None
    except (TypeError, ValueError):
        return None


def _safe_date(val):
    if val is None or (hasattr(val, "__class__") and val.__class__.__name__ == "NaTType"):
        return None
    try:
        import pandas as pd
        return val.date() if hasattr(val, "date") else None
    except Exception:
        return None
