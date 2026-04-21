"""Tests de integración de la API — requieren base de datos de test."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.main import app
from src.db.models import Base, DimEmpresa, Declaracion
from src.db.session import get_db_dependency

TEST_DB_URL = "sqlite:///:memory:"  # SQLite para tests rápidos

engine_test = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db_dependency] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine_test)
    db = TestingSession()
    empresa = DimEmpresa(nit="860503159", razon_social="EMPRESA TEST SAS")
    db.add(empresa)
    db.flush()
    from datetime import date
    decl = Declaracion(
        num_formulario="TEST001",
        empresa_id=empresa.id,
        anio=2025,
        valor_fob_usd=50000.0,
        total_peso_bruto_kg=500.0,
        cod_pais_destino="EC",
        pais_destino="Ecuador",
        fecha_aceptacion=date(2025, 10, 9),
        modo_transporte="Transporte carretero",
        archivo_fuente="test.xlsx",
    )
    db.add(decl)
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine_test)


client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_declaraciones_endpoint():
    r = client.get("/api/v1/declaraciones")
    assert r.status_code == 200
    body = r.json()
    assert "total" in body
    assert "data" in body
    assert body["total"] >= 1


def test_declaraciones_filtro_nit():
    r = client.get("/api/v1/declaraciones", params={"nit": "860503159"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert all(d["nit_exportador"] == "860503159" for d in data)


def test_declaraciones_paginacion():
    r = client.get("/api/v1/declaraciones", params={"page": 1, "page_size": 10})
    assert r.status_code == 200
    assert r.json()["page"] == 1
    assert r.json()["page_size"] == 10
