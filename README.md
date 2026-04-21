# Export Analytics — Sistema de Análisis de Exportaciones DIAN

> Sistema completo de ingesta, procesamiento, almacenamiento, análisis y visualización de declaraciones de exportación del **Formulario 600 (DEX)** de la DIAN — Colombia.

---

## Tabla de Contenidos

- [Contexto del Dataset](#-contexto-del-dataset)
- [Insights del Análisis Real](#-insights-del-análisis-real)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Stack Tecnológico](#-stack-tecnológico)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Modelo de Datos](#-modelo-de-datos)
- [API REST — Endpoints](#-api-rest--endpoints)
- [Machine Learning](#-machine-learning)
- [Prerrequisitos](#-prerrequisitos)
- [Instalación y Configuración](#-instalación-y-configuración)
- [Guía de Ejecución](#-guía-de-ejecución)
  - [Modo Local (desarrollo)](#modo-local-desarrollo)
  - [Modo Docker (producción)](#modo-docker-producción)
- [Ejecutar el ETL](#-ejecutar-el-etl)

- [Ejecutar los Tests](#-ejecutar-los-tests)
- [CI/CD con GitHub Actions](#-cicd-con-github-actions)
- [Decisiones Técnicas](#-decisiones-técnicas)
- [Mejoras Futuras](#-mejoras-futuras)

---

## Contexto del Dataset

Los archivos de origen son exportaciones de la DIAN del **Formulario 600 — DEX (Declaración de Exportación)**, cubriendo el **Q4 2025** (octubre, noviembre y diciembre).

| Característica | Valor |
|---|---|
| Archivos fuente | 13 archivos XLSX |
| Periodo cubierto | Octubre — Diciembre 2025 |
| Declaraciones únicas | **520,187** |
| Columnas por archivo | **109** |
| FOB Total Exportado | **$54,294,834,075 USD** |
| Empresas exportadoras | ~35,000 únicas |

### Estructura de los archivos fuente

```
D:/trabajo/fiscalia/
├── Exportaciones-octubre-2025/
│   ├── F600_20251009.xlsx    (47,559 filas)
│   ├── F600_20251017.xlsx    (45,958 filas)
│   ├── F600_20251025.xlsx    (48,452 filas)
│   └── F600_20251031.xlsx    (40,256 filas)
├── Exportaciones-noviembre-2025/
│   ├── 600_20251109.xlsx     (42,305 filas)
│   ├── 600_20251117.xlsx     (46,600 filas)
│   ├── 600_20251125.xlsx     (48,190 filas)
│   └── 600_20251130.xlsx     (29,935 filas)
└── Exportaciones-diciembre-2025/
    ├── 600_20251207.xlsx     (79,673 filas)
    ├── 600_20251213.xlsx     (73,722 filas)
    ├── 600_20251219.xlsx     (67,762 filas)
    ├── 600_20251225.xlsx     (30,441 filas)
    └── 600_20251231.xlsx     (28,511 filas)
```

> Cada fila del XLSX corresponde a una **serie** (ítem de producto). El sistema deduplica por `C4NUMFORMULARIO` para construir la tabla de **declaraciones** (cabecera), y almacena las series por separado.

---

## Insights del Análisis Real

### Top 10 Empresas Exportadoras (Oct-Dic 2025)

```
  Empresa                                     FOB (M USD)    %     Decl.   Países
  ──────────────────────────────────────────  ───────────  ─────  ──────  ──────
  AVIANCA (AEROVIAS DEL CONTINENTE AMERICANO)  $19,244 M   58.8%   2,834     31
  ECOPETROL S.A.                                $5,664 M   17.3%     418     27
  DRUMMOND LTD                                  $2,720 M    8.3%   1,785     24
  CARBONES DEL CERREJÓN LIMITED                   $955 M    2.9%     243     21
  FRONTERA ENERGY COLOMBIA CORP                   $814 M    2.5%      30      3
  C.I. TRAFIGURA PETROLEUM COLOMBIA S.A.S.        $783 M    2.4%   4,911      4
  MABE COLOMBIA S.A.S                             $681 M    2.1%   1,015     20
  LA LINDA COFFEE ROASTERS SAS                    $632 M    1.9%       6      2
  REFINERÍA DE CARTAGENA S.A.S (REFICAR)          $621 M    1.9%      58      9
  C.I. UNIÓN DE BANANEROS DE URABÁ (UNIBAN)       $605 M    1.8%   3,082     26
```

> ⚠️ **Las 10 primeras empresas concentran el 99.9% del FOB total** — mercado oligopólico dominado por petróleo, carbón y servicios aéreos.

### Distribución por Modo de Transporte

```
  Marítimo          ████████████████████████████░  $27,519 M  (50.7%)
  Aéreo             ███████████████████████████░░  $25,087 M  (46.2%)
  Carretero         ██░░░░░░░░░░░░░░░░░░░░░░░░░░░     $944 M   (1.7%)
  Inst. Fijas       █░░░░░░░░░░░░░░░░░░░░░░░░░░░░     $310 M   (0.6%)
```

> La altísima participación aérea (~46%) es atípica a nivel mundial y refleja el peso de AVIANCA como exportador de servicios/carga aérea.

### Top 10 Países Destino

```
  🇺🇸  Estados Unidos   $17,861 M  ████████████████████░░░
  🇪🇨  Ecuador           $7,592 M  █████████░░░░░░░░░░░░░░
  🇲🇽  México            $3,261 M  ████░░░░░░░░░░░░░░░░░░░
  🇵🇦  Panamá            $2,943 M  ███░░░░░░░░░░░░░░░░░░░░
  🇨🇳  China             $1,377 M  █░░░░░░░░░░░░░░░░░░░░░░
  🇳🇱  Países Bajos      $1,365 M  █░░░░░░░░░░░░░░░░░░░░░░
  🇩🇪  Alemania          $1,339 M  █░░░░░░░░░░░░░░░░░░░░░░
  🇧🇷  Brasil            $1,318 M  █░░░░░░░░░░░░░░░░░░░░░░
  🇮🇳  India             $1,178 M  █░░░░░░░░░░░░░░░░░░░░░░
  🇨🇱  Chile             $1,128 M  █░░░░░░░░░░░░░░░░░░░░░░
```

---

## Arquitectura del Sistema

```
┌─────────────────────��─────────────────────────────────────────────┐
│                          FUENTES DE DATOS                           │
│        13 archivos XLSX  ·  629,364 filas  ·  109 columnas          │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        CAPA ETL  (src/etl/)                         │
│                                                                     │
│  column_map.py      cleaner.py          loader.py                   │
│  ┌─────────────┐   ┌──────────────┐    ┌──────────────────────┐     │
│  │ Mapeo       │──▶│ Limpieza     │──▶│ Upsert idempotente   │     │
│  │ 109 cols    │   │ Nulos/tipos  │    │ Chunks de 10K rows   │     │
│  │ → internos  │   │ Normalización│    │ Transacciones        │     │
│  └─────────────┘   └──────────────┘    └──────────────────────┘     │
│                         pipeline.py (orquestador)                   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     CAPA STORAGE  (src/db/)                         │
│                                                                     │
│   PostgreSQL 16                                                     │
│   ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐    │
│   │  dim_empresas    │  │  declaraciones   │  │    series      │    │
│   │  ~35K empresas   │  │  ~520K registros │  │  ~629K líneas  │    │
│   └──────────────────┘  └──────────────────┘  └────────────────┘    │
│   ┌──────────────────────┐  ┌────────────────────────────────────┐  │
│   │  mv_empresas_top     │  │  mv_tendencia_mensual              │  │
│   │  (materializada)     │  │  (materializada, refresh post-ETL) │  │
│   └──────────────────────┘  └────────────────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
               ┌─────────────────┴──────────────────┐
               │                                    │
               ▼                                    ▼
┌──────────────────────────┐         ┌──────────────────────────────┐
│    CAPA API  (src/api/)  │         │   CAPA ML  (src/ml/)         │
│                          │         │                              │
│  FastAPI + SQLAlchemy    │         │  Random Forest Regressor     │
│  Pydantic v2 schemas     │         │  TimeSeriesSplit (3 folds)   │
│  6 endpoints REST        │         │  Features lag-1/2/3, rolling │
│  Paginación + filtros    │         │  Target: log1p(FOB_USD)      │
│  /docs (Swagger UI)      │         │  Predicción próximo mes      │
└────────────┬─────────────┘         └──────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   CAPA FRONTEND  (frontend/)                        │
│                                                                     │
│   Streamlit + Plotly                                                │
│   ┌────────────┐ ┌─────────────────┐ ┌──────────┐ ┌─────────────┐   │
│   │ KPIs       │ │ Top Empresas    │ │Tendencia │ │Declaraciones│   │
│   │ Globales   │ │ Bar + Scatter   │ │ Mensual  │ │ Buscador    │   │
│   │            │ │ + Pie chart     │ │ + Mapa   │ │ Paginado    │   │
│   └────────────┘ └─────────────────┘ └──────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Patrón de diseño: Clean Architecture por capas

Cada capa tiene una única responsabilidad y **no conoce las capas superiores**:

- `etl/` lee archivos y escribe en BD — no sabe que existe una API
- `api/` lee de BD y responde HTTP — no sabe cómo se cargaron los datos
- `ml/` consume BD y produce modelos — totalmente independiente
- `frontend/` consume la API — nunca accede a BD directamente

---

## Stack Tecnológico

| Capa | Tecnología | Versión | Justificación |
|---|---|---|---|
| **Lenguaje** | Python | 3.11+ | f-strings mejoradas, `tomllib` nativo, `match` |
| **Gestor deps** | Poetry | 1.8.3 | `pyproject.toml` único, lockfile reproducible |
| **ETL** | pandas + numpy | 2.2 / 1.26 | Estándar de facto; `read_excel` chunked para 629K filas |
| **XLSX** | openpyxl | 3.1 | Motor requerido por pandas para `.xlsx` |
| **Base de datos** | PostgreSQL | 16 | ACID, vistas materializadas, extensión `unaccent`, extensible |
| **ORM** | SQLAlchemy | 2.0 | Async-ready, typed, upsert nativo |
| **API** | FastAPI | 0.111 | Async I/O, Pydantic v2 nativo, OpenAPI automático |
| **Validación** | Pydantic | 2.7 | 5-20x más rápido que v1; validación en runtime |
| **ML** | scikit-learn | 1.5 | `RandomForestRegressor` + `TimeSeriesSplit` |
| **Frontend** | Streamlit | 1.35 | Dashboard analítico en horas, no en semanas |
| **Gráficos** | Plotly | 5.22 | Interactividad nativa, choropleth maps, treemaps |
| **Logging** | Loguru | 0.7 | Structured logging sin configuración verbosa |
| **Contenedores** | Docker + Compose | 26+ | Aislamiento reproducible por servicio |
| **CI/CD** | GitHub Actions | — | 4 etapas: lint → test → build → deploy |
| **Linting** | Ruff + mypy | 0.4 / 1.10 | Ruff reemplaza flake8+isort en un binario Rust |

---

## Estructura del Proyecto

```
export-analytics/
│
├── 📄 pyproject.toml              # Dependencias y configuración (Poetry)
├── 📄 Makefile                    # Comandos de orquestación
├── 📄 docker-compose.yml          # Orquestación de servicios
├── 📄 .env.example                # Variables de entorno de referencia
│
├── 📂 src/                        # Código fuente principal
│   ├── config.py                  # Settings centralizados (pydantic-settings)
│   │
│   ├── 📂 db/                     # Capa de datos
│   │   ├── models.py              # ORM: dim_empresas, declaraciones, series
│   │   ├── session.py             # Connection pool + context manager
│   │   └── init_db.py             # DDL + vistas materializadas
│   │
│   ├── 📂 etl/                    # Pipeline de ingesta
│   │   ├── column_map.py          # Mapeo XLSX → nombres canónicos
│   │   ├── cleaner.py             # Limpieza: nulos, tipos, normalización
│   │   ├── loader.py              # Upsert idempotente a PostgreSQL
│   │   ├── pipeline.py            # Orquestador: lee → limpia → carga
│   │   └── exploratory_analysis.py # Análisis directo sobre XLSX
│   │
│   ├── 📂 api/                    # API REST
│   │   ├── main.py                # FastAPI app + CORS + lifespan
│   │   ├── routes.py              # 6 endpoints con validación
│   │   ├── queries.py             # SQL analítico centralizado
│   │   └── schemas.py             # Pydantic v2 request/response models
│   │
│   └── 📂 ml/                     # Machine Learning
│       └── predictor.py           # Entrenamiento + predicción FOB
│
├── 📂 frontend/
│   └── app.py                     # Dashboard Streamlit (4 tabs + KPIs)
│
├── 📂 tests/
│   ├── test_etl_cleaner.py        # 9 unit tests de limpieza
│   └── test_api.py                # 4 integration tests de API
│
├── 📂 docker/
│   ├── Dockerfile.api             # Imagen FastAPI (uvicorn multi-worker)
│   ├── Dockerfile.etl             # Imagen ETL (job one-shot)
│   └── Dockerfile.frontend        # Imagen Streamlit
│
└── 📂 .github/workflows/
    └── ci.yml                     # Pipeline CI/CD (lint → test → build → deploy)
```

---

## Modelo de Datos

### Diagrama Entidad-Relación

```
┌─────────────────────┐
│    dim_empresas     │
├─────────────────────┤
│ PK  id              │
│     nit (UNIQUE)    │◄──────────────────────────┐
│     razon_social    │                           │
│     created_at      │                           │
│     updated_at      │                           │
└─────────────────────┘                           │
                                                  │  1:N
┌───────────────────────────────────────────────────────────────┐
│                        declaraciones                          │
├───────────────────────────────────────────────────────────────┤
│ PK  id                                                        │
│     num_formulario (UNIQUE)          ← índice único           │
│ FK  empresa_id → dim_empresas.id     ← índice compuesto       │
│     anio                                                      │
│     nit_declarante                   (agencia de aduanas)     │
│     razon_social_declarante                                   │
│     razon_social_destinatario                                 │
│     pais_destino / cod_pais_destino  ← índice                 │
│     modo_transporte / incoterms                               │
│     valor_fob_usd                    ← índice                 │
│     valor_fletes_usd / seguros_usd                            │
│     total_peso_bruto_kg                                       │
│     total_series / total_bultos                               │
│     fecha_aceptacion                 ← índice                 │
│     cod_aduana_despacho              ← índice                 │
│     archivo_fuente                   (trazabilidad ETL)       │
│     cargado_en                                                │
└───────────────────────────────────────────────────┬───────────┘
                                                    │
                                                    │  1:N
┌───────────────────────────────────────────────────▼───────────┐
│                           series                              │
├───────────────────────────────────────────────────────────────┤
│ PK  id                                                        │
│ FK  declaracion_id → declaraciones.id  ← índice               │
│     num_serie                                                 │
│     subpartida (10 dígitos)            ← índice               │
│     nomenclatura                                              │
│     cantidad_fisica / cod_unidad_fisica                       │
│     cantidad_comercial / cod_unidad_comercial                 │
│     peso_bruto_kg / peso_neto_kg                              │
│     valor_fob_usd                      ← índice               │
│     descripcion (TEXT)                                        │
│     marcas (TEXT)                                             │
│     cod_pais_origen                                           │
└───────────────────────────────────────────────────────────────┘

Vistas materializadas (pre-calculadas, refresh automático al finalizar el ETL):

  mv_empresas_top        → ranking empresas por FOB, declaraciones, países
  mv_tendencia_mensual   → serie temporal mensual por país/modo transporte
```

### DDL principal (PostgreSQL)

```sql
-- Ejemplo de índices estratégicos
CREATE INDEX ix_declaraciones_empresa_fecha
    ON declaraciones (empresa_id, fecha_aceptacion);

CREATE INDEX ix_declaraciones_pais_destino
    ON declaraciones (cod_pais_destino);

-- Extensión para búsqueda sin acentos (instalada automáticamente por el ETL)
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Vista materializada con agregaciones NaN-safe
CREATE MATERIALIZED VIEW mv_empresas_top AS
SELECT
    e.nit,
    e.razon_social,
    COUNT(DISTINCT d.id)                                                    AS total_declaraciones,
    COALESCE(SUM(d.valor_fob_usd) FILTER (WHERE d.valor_fob_usd::text != 'NaN'), 0) AS fob_total_usd,
    COUNT(DISTINCT d.cod_pais_destino)                                      AS paises_destino
FROM dim_empresas e
JOIN declaraciones d ON d.empresa_id = e.id
WHERE d.valor_fob_usd IS NOT NULL
  AND d.valor_fob_usd::text != 'NaN'
GROUP BY e.nit, e.razon_social
WITH DATA;

CREATE UNIQUE INDEX uix_mv_empresas_top_nit ON mv_empresas_top (nit);
```

---

## API REST — Endpoints

Base URL: `http://localhost:8000`  
Documentación interactiva: `http://localhost:8000/docs`

| Método | Ruta | Descripción | Parámetros |
|---|---|---|---|
| `GET` | `/health` | Health check | — |
| `GET` | `/api/v1/metricas` | KPIs globales del dataset | — |
| `GET` | `/api/v1/empresas/top` | Top N empresas por FOB | `limit` (1-100, default 10) |
| `GET` | `/api/v1/tendencia/mensual` | Serie temporal mensual | `pais_destino` (ISO-2 o nombre), `modo_transporte` (sin acentos) |
| `GET` | `/api/v1/declaraciones` | Búsqueda paginada | `nit`, `pais` (ISO-2 o nombre), `fecha_desde`, `fecha_hasta`, `page`, `page_size` |
| `GET` | `/api/v1/analisis/paises` | Distribución por país destino | `top_n` |
| `GET` | `/api/v1/analisis/subpartidas` | Top subpartidas arancelarias con descripción del producto | `top_n` |

### Ejemplos de uso

```bash
# KPIs globales
curl http://localhost:8000/api/v1/metricas

# Top 5 empresas
curl "http://localhost:8000/api/v1/empresas/top?limit=5"

# Tendencia mensual filtrada por país
curl "http://localhost:8000/api/v1/tendencia/mensual?pais_destino=US"

# Declaraciones de ECOPETROL, paginadas
curl "http://localhost:8000/api/v1/declaraciones?nit=899999068&page=1&page_size=20"

# Distribución top 15 países
curl "http://localhost:8000/api/v1/analisis/paises?top_n=15"
```

### Ejemplo de respuesta — `/api/v1/metricas`

```json
{
  "total_declaraciones": 520187,
  "total_empresas": 34821,
  "total_paises_destino": 148,
  "fob_total_usd": 54294834075.0,
  "peso_total_kg": 98432156.4,
  "periodo_inicio": "2025-10-01",
  "periodo_fin": "2025-12-31"
}
```

---

## Machine Learning

### Modelo: Predicción de FOB mensual por empresa

**Objetivo:** dado el historial de una empresa, predecir el valor FOB que exportará el próximo mes.

**Algoritmo:** `RandomForestRegressor` con validación `TimeSeriesSplit`

```
  Datos históricos (empresa × mes)
         │
         ▼
  Feature Engineering
  ┌─────────────────────────────────────────────────────┐
  │  fob_lag1      ← FOB del mes anterior               │
  │  fob_lag2/3    ← lags adicionales                   │
  │  fob_rolling3  ← media móvil 3 meses                │
  │  pct_cambio    ← variación % respecto a lag1        │
  │  mes_numero    ← estacionalidad (1-12)              │
  │  trimestre     ← agrupación estacional              │
  │  num_paises    ← diversificación de destinos        │
  │  es_aereo      ← modo transporte dominante (0/1)    │
  │  es_maritimo   ← idem                               │
  └─────────────────────────────────────────────────────┘
         │
         ▼
  Target: log1p(fob_total)   ← normaliza distribución asimétrica
         │
         ▼
  TimeSeriesSplit (3 folds)  ← sin data leakage temporal
  ┌─────────┬─────────┬─────────┐
  │ Fold 1  │ Fold 2  │ Fold 3  │
  │ Train → │ Train ──┤ Train ──┤→ Test
  └─────────┴─────────┴─────────┘
         │
         ▼
  Modelo final (300 árboles) + joblib serialization
```

**Métricas de evaluación:**

| Métrica | Descripción |
|---|---|
| MAE (Mean Absolute Error) | Error promedio en USD — interpretable por negocio |
| RMSE | Penaliza outliers — relevante dado el rango $100 a $6B |
| R² (escala log) | Varianza explicada en escala normalizada |

**Intervalo de confianza:** calculado usando la desviación estándar de las predicciones individuales de cada árbol del bosque (`std` de `tree.predict()` sobre todos los estimadores).

### Entrenar el modelo

```bash
# Con Make
make train

# Directamente
poetry run python -c "
from src.db.session import get_db
from src.ml.predictor import run_training_pipeline
with get_db() as db:
    metrics = run_training_pipeline(db)
    print(metrics)
"
```

El modelo se guarda en `./ml_models/fob_predictor.joblib` junto con `fob_predictor_metrics.json`.

---

## ✅ Prerrequisitos

### Software requerido

| Herramienta | Versión mínima | Verificar |
|---|---|---|
| Python | 3.11+ | `python --version` |
| pip | 23+ | `pip --version` |
| Docker | 24+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| PostgreSQL (local) | 14+ | `psql --version` *(solo para modo local)* |
| Git | 2.40+ | `git --version` |

### Instalar Poetry (gestor de dependencias)

```bash
# Linux / macOS
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# Verificar
poetry --version
```

---

## ⚙️ Instalación y Configuración

### 1. Clonar o posicionarse en el directorio del proyecto

```bash
cd export-analytics/
```

### 2. Instalar dependencias con Poetry

```bash
poetry install
```

Esto crea un virtualenv aislado e instala todas las dependencias del `pyproject.toml`.

### 3. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con tus valores:

```dotenv
# Conexión a PostgreSQL
DATABASE_URL=postgresql://postgres:tu_password@localhost:5432/exportaciones

# Directorio donde están los XLSX (relativo o absoluto)
# Apunta al directorio PADRE que contiene las carpetas Exportaciones-*
DATA_DIR=../

# Nivel de log (DEBUG | INFO | WARNING)
LOG_LEVEL=INFO

# API
API_HOST=0.0.0.0
API_PORT=8000

# Directorio para guardar modelos ML
ML_MODELS_DIR=./ml_models
```

### 4. Crear la base de datos en PostgreSQL

```bash
# Conectarse a PostgreSQL como superusuario
psql -U postgres -c "CREATE DATABASE exportaciones;"
```

---

## 🚀 Guía de Ejecución

### Modo Local (desarrollo)

#### Paso 1 — Inicializar el esquema y ejecutar el ETL

```bash
# Crea tablas, índices y vistas materializadas
poetry run python -m src.db.init_db

# Ejecuta el pipeline ETL completo
# DATA_DIR debe apuntar al directorio con los XLSX
make etl DATA_DIR=../

# Equivalente directo:
poetry run python -m src.etl.pipeline ../
```

El ETL procesa los 13 archivos XLSX en chunks de 10,000 filas. El tiempo estimado es **15-25 minutos** dependiendo de los recursos de la máquina.

Salida esperada:
```
09:15:32 | INFO    | Archivos encontrados: 13
09:15:32 | INFO    | Creando esquema de base de datos...
09:15:33 | SUCCESS | Tablas creadas exitosamente.
09:15:33 | INFO    | Procesando: F600_20251009.xlsx
09:16:48 | SUCCESS | F600_20251009.xlsx: 47559 decl, 47559 series cargadas
...
10:38:15 | SUCCESS | ETL completado: 520187 declaraciones, 629364 series
```

#### Paso 2 — Iniciar la API

```bash
poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

La API estará disponible en:
- API base: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### Paso 3 — Iniciar el Frontend (terminal separada)

```bash
poetry run streamlit run frontend/app.py --server.port 8501
```

Dashboard disponible en: http://localhost:8501

#### Paso 4 — Entrenar el modelo ML (opcional)

```bash
make train
```

---

### Modo Docker (producción)

#### Inicio rápido — todos los servicios

```bash
# Construir y levantar PostgreSQL + API + Frontend
DATA_DIR=$(realpath ../) docker-compose up -d postgres api frontend

# Ver estado de los servicios
docker-compose ps

# Ver logs en tiempo real
docker-compose logs -f api frontend
```

#### Ejecutar el ETL en Docker

```bash
# El ETL es un job one-shot que lee los XLSX montados como volumen
DATA_DIR=$(realpath ../) docker-compose run --rm etl
```

> El directorio `DATA_DIR` se monta como volumen read-only en `/data` dentro del contenedor ETL.

#### Comandos Docker útiles

```bash
# Construir imágenes manualmente
docker build -f docker/Dockerfile.api -t export-analytics-api .
docker build -f docker/Dockerfile.frontend -t export-analytics-frontend .
docker build -f docker/Dockerfile.etl -t export-analytics-etl .

# Detener todos los servicios
docker-compose down

# Detener y eliminar volúmenes (¡borra los datos de PostgreSQL!)
docker-compose down -v

# Reiniciar solo la API
docker-compose restart api

# Ejecutar un comando en el contenedor de la API
docker-compose exec api python -m src.db.init_db

# Ver logs de un servicio específico
docker-compose logs -f postgres
docker-compose logs --tail=100 api

# Acceder a la shell del contenedor
docker-compose exec api bash

# Conectarse a PostgreSQL dentro de Docker
docker-compose exec postgres psql -U postgres -d exportaciones
```

#### Puertos expuestos

| Servicio | Puerto host | Puerto contenedor |
|---|---|---|
| PostgreSQL | `5432` | `5432` |
| API FastAPI | `8000` | `8000` |
| Frontend Streamlit | `8501` | `8501` |

#### Variables de entorno para Docker

Crear un archivo `.env` en la raíz (o pasarlas directamente):

```bash
# .env para docker-compose
POSTGRES_PASSWORD=secreto123
DATA_DIR=/ruta/absoluta/a/los/xlsx
```

---

## 🧪 Ejecutar los Tests

### Instalación de dependencias de desarrollo

```bash
poetry install --with dev
```

### Ejecutar todos los tests

```bash
poetry run pytest tests/ -v
```

Salida esperada:

```
====================== test session starts ======================
platform win32 -- Python 3.11.x
collected 12 items

tests/test_etl_cleaner.py::test_nit_limpieza              PASSED
tests/test_etl_cleaner.py::test_nit_con_guion             PASSED
tests/test_etl_cleaner.py::test_valores_negativos_a_nan   PASSED
tests/test_etl_cleaner.py::test_fecha_parsing             PASSED
tests/test_etl_cleaner.py::test_drop_sin_nit              PASSED
tests/test_etl_cleaner.py::test_razon_social_upper        PASSED
tests/test_etl_cleaner.py::test_clean_series_negativos    PASSED
tests/test_etl_cleaner.py::test_clean_series_subpartida   PASSED
tests/test_api.py::test_health                            PASSED
tests/test_api.py::test_declaraciones_endpoint            PASSED
tests/test_api.py::test_declaraciones_filtro_nit          PASSED
tests/test_api.py::test_declaraciones_paginacion          PASSED

====================== 12 passed in 1.24s =======================
```

### Opciones de pytest

```bash
# Solo tests del ETL
poetry run pytest tests/test_etl_cleaner.py -v

# Solo tests de la API
poetry run pytest tests/test_api.py -v

# Con cobertura de código
poetry run pytest tests/ --cov=src --cov-report=html

# Parar en el primer fallo
poetry run pytest tests/ -x

# Ver output de print/logs
poetry run pytest tests/ -v -s

# Filtrar por nombre de test
poetry run pytest tests/ -k "test_nit"
```

### Linting y type checking

```bash
# Por separado:
poetry run ruff check src/           # Linting (PEP8, imports, naming)
poetry run mypy src/ --ignore-missing-imports  # Type checking estático
```

---

## 🔄 CI/CD con GitHub Actions

El pipeline `.github/workflows/ci.yml` define **4 etapas** que se ejecutan en cada `push` o `pull_request`:

```
Push a main/develop
       │
       ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│   1. LINT   │────▶│  2. TESTS   │────▶│  3. DOCKER BUILD│────▶│  4. DEPLOY   │
│             │     │             │     │                 │     │ (solo main)  │
│ ruff check  │     │ pytest      │     │ docker build    │     │              │
│ mypy        │     │ PostgreSQL  │     │ api + frontend  │     │ Push GHCR    │
│             │     │ en service  │     │                 │     │              │
└─────────────┘     └─────────────┘     └─────────────────┘     └──────────────┘
```

- **Etapa 1 (Lint):** Ruff + mypy sobre todo `src/`
- **Etapa 2 (Tests):** pytest con PostgreSQL real como service container
- **Etapa 3 (Docker Build):** verifica que las imágenes buildean correctamente
- **Etapa 4 (Deploy):** solo en `push` a `main` — sube imágenes a GitHub Container Registry

### Configurar el repositorio de GitHub

```bash
git init
git add .
git commit -m "feat: sistema completo de análisis de exportaciones DIAN"
git remote add origin https://github.com/tu-usuario/export-analytics.git
git push -u origin main
```

El workflow se activará automáticamente en el próximo push.

---

## 🔧 Decisiones Técnicas

### ¿Por qué FastAPI y no Django REST?

Django REST requiere un ORM propio (Django ORM) que duplicaría el trabajo con SQLAlchemy. FastAPI + Pydantic v2 ofrece validación en runtime, serialización 5x más rápida, y OpenAPI automático. Para una API de solo lectura sobre datos analíticos, el overhead de Django no se justifica.

### ¿Por qué Streamlit y no React/Next.js?

El consumidor final es equipo de analítica/fiscalía, no usuarios externos. Streamlit permite construir el dashboard en horas con Python puro. React añadiría un build pipeline Node.js, gestión de estado, y semanas de desarrollo para el mismo resultado visual.

### ¿Por qué chunked ETL (10K rows/tx)?

Con 629K filas en una transacción única: (a) un timeout de BD aborta todo el trabajo; (b) el uso de RAM puede alcanzar 8-12 GB; (c) no hay progreso observable. Los chunks de 10K permiten commits intermedios, recuperabilidad parcial, y logging de progreso.

### ¿Por qué vistas materializadas?

Las queries analíticas sobre `JOIN(declaraciones, series, dim_empresas)` con 500K+ filas toman 3-8 segundos. Las vistas materializadas pre-calculan los resultados y responden en < 50ms. El refresh se ejecuta automáticamente al finalizar el pipeline ETL con `REFRESH MATERIALIZED VIEW` (sin `CONCURRENTLY`, ya que los índices únicos incluyen columnas nullable). Las agregaciones usan `FILTER (WHERE valor_fob_usd::text != 'NaN')` para excluir valores NaN de PostgreSQL que de otro modo contaminarían los totales.

### ¿Por qué `log1p()` en el modelo ML?

La distribución de FOB cubre **7 órdenes de magnitud**: desde exportadores con $100 hasta Avianca con $6,000,000,000. Una transformación logarítmica es el estándar para variables económicas con esta distribución. `log1p` (log(1+x)) maneja correctamente los ceros.

### ¿Por qué `TimeSeriesSplit` y no K-Fold?

K-Fold aleatorio en series temporales produce **data leakage**: el modelo entrena con datos del futuro para predecir el pasado. `TimeSeriesSplit` garantiza que cada fold solo usa datos anteriores para entrenar — esencial para validación honesta de modelos predictivos.

---

## 📄 Licencia

Uso interno — Datos de la DIAN Colombia.

---

*Generado con Clean Architecture · FastAPI · PostgreSQL · scikit-learn · Streamlit · Docker*
