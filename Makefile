.PHONY: install setup etl api frontend train analyze test lint docker-up docker-down

DATA_DIR ?= ../

install:
	pip install poetry==1.8.3
	poetry install

setup: install
	cp .env.example .env
	@echo "Edita .env con tu DATABASE_URL antes de continuar"

# Inicializar BD y ejecutar ETL
etl:
	poetry run python -m src.db.init_db
	poetry run python -m src.etl.pipeline $(DATA_DIR)

# Iniciar API
api:
	poetry run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Iniciar Frontend
frontend:
	poetry run streamlit run frontend/app.py --server.port 8501

# Entrenar modelo ML
train:
	poetry run python -c "
from src.db.session import get_db
from src.ml.predictor import run_training_pipeline
with get_db() as db:
    metrics = run_training_pipeline(db)
    print('Métricas:', metrics)
"

# Análisis exploratorio (sin BD, directo desde XLSX)
analyze:
	poetry run python -m src.etl.exploratory_analysis $(DATA_DIR)

# Tests
test:
	poetry run pytest tests/ -v

# Lint
lint:
	poetry run ruff check src/
	poetry run mypy src/ --ignore-missing-imports

# Docker
docker-up:
	DATA_DIR=$(DATA_DIR) docker-compose up -d postgres api frontend

docker-down:
	docker-compose down

docker-etl:
	DATA_DIR=$(DATA_DIR) docker-compose run --rm etl

logs:
	docker-compose logs -f api frontend
