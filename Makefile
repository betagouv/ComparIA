.PHONY: help install install-backend install-frontend dev dev-redis dev-backend dev-frontend dev-controller build-frontend clean redis

# Variables
PYTHON := python3
UV := uv
NPM := yarn
BACKEND_PORT := 8001
FRONTEND_PORT := 5173
CONTROLLER_PORT := 21001

# si non défini (utiliser les valeurs de dev local avec docker compose)
COMPARIA_DB_URI ?= postgresql://postgres:postgres@localhost:5432/languia
COMPARIA_REDIS_HOST ?= localhost
# Exporter pour les sous-commandes
export COMPARIA_DB_URI
export COMPARIA_REDIS_HOST

help: ## Display this help
	@echo "Available commands for compar:IA:"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'

install: install-backend install-frontend ## Install all dependencies (backend + frontend)

install-backend: ## Install Python backend dependencies with uv
	@echo "Installing backend dependencies..."
	@if ! command -v uv &> /dev/null; then \
		echo "uv is not installed. Installing..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi
	$(UV) sync

install-frontend: ## Install npm frontend dependencies
	@echo "Installing frontend dependencies..."
	cd frontend && $(NPM) install || npm install --legacy-peer-deps

# generate the file to init db in postgres docker
db-generate-init: ## Generate docker/data/init-db.sql from schema files
	@bash docker/generate-init-db.sh

## Launch and init Postgres database using docker compose
db:
	@$(MAKE) db-generate-init
	@echo "Starting PostgreSQL database..."
	cd docker && docker compose up postgres -d

redis: ## Launch Redis using docker compose
	@echo "Starting Redis..."
	cd docker && docker compose up redis -d

dev-full: ## Launch backend and frontend with Postgres and Redis (Ctrl+C to stop)
	@echo "Launching compar:IA with Postgres and Redis..."
	@echo "Starting Redis..."
	@cd docker && docker compose up redis -d || echo "Redis already running or failed to start"
	@$(MAKE) db
	@echo "Backend: http://localhost:$(BACKEND_PORT)"
	@echo "Frontend: http://localhost:$(FRONTEND_PORT)"
	@$(MAKE) -j 2 dev-backend dev-frontend

dev: ## Launch backend and frontend without Redis (Ctrl+C to stop)
	@echo "Launching compar:IA..."
	@echo "Backend: http://localhost:$(BACKEND_PORT)"
	@echo "Frontend: http://localhost:$(FRONTEND_PORT)"
	@$(MAKE) -j 2 dev-backend dev-frontend

dev-backend: ## Launch only the backend (FastAPI + Gradio)
	@echo "Starting backend on port $(BACKEND_PORT)..."
	$(UV) run uvicorn main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT) --timeout-graceful-shutdown 1

dev-frontend: ## Launch only the frontend (Vite + SvelteKit)
	@echo "Starting frontend on port $(FRONTEND_PORT)..."
	cd frontend && $(NPM) run dev

dev-controller: ## Launch the dashboard controller
	@echo "Starting controller on port $(CONTROLLER_PORT)..."
	$(UV) run uvicorn controller:app --reload --host 0.0.0.0 --port $(CONTROLLER_PORT)

build-frontend: ## Build the frontend for production
	@echo "Building frontend..."
	cd frontend && $(NPM) run build

lint-frontend: ## Check frontend code
	@echo "Checking frontend code..."
	cd frontend && $(NPM) run lint

format-frontend: ## Format frontend code
	@echo "Formatting frontend code..."
	cd frontend && $(NPM) run format

# i18n utilities
i18n-clean-locales: ## Remove locales keys not present in fr
	@echo "Cleaning frontend locales keys..."
	cd frontend/locales && python maintenance.py

i18n-build-suggestions: ## generate frontend i18n prompt suggestions file
	@echo "Generating frontend prompt suggestions..."
	$(UV) run python -m utils.suggestions.build_suggestions

i18n-build-news: ## generate news files
	@echo "Generating news files..."
	$(UV) run python -m utils.news.build_news

dev-full-reset-data:
	@echo "Removing docker dev data (volumes)..."
	@cd docker && docker down -v
	@$(MAKE) dev-full



# db-schema-init: ## Initialize database schema
# 	@echo "Initializing database schema..."
# 	@if [ -z "$$DATABASE_URI" ]; then \
# 		echo "Error: DATABASE_URI is not defined"; \
# 		exit 1; \
# 	fi
# 	@echo "Executing SQL scripts in utils/schemas/..."
# 	psql $$DATABASE_URI -f utils/schemas/conversations.sql
# 	psql $$DATABASE_URI -f utils/schemas/votes.sql
# 	psql $$DATABASE_URI -f utils/schemas/reactions.sql
# 	psql $$DATABASE_URI -f utils/schemas/logs.sql

# db-migrate: ## Apply database migrations
# 	@echo "Applying migrations..."
# 	@if [ -z "$$DATABASE_URI" ]; then \
# 		echo "Error: DATABASE_URI is not defined"; \
# 		exit 1; \
# 	fi
# 	psql $$DATABASE_URI -f utils/schemas/migrations/conversations_13102025.sql
# 	psql $$DATABASE_URI -f utils/schemas/migrations/reactions_13102025.sql

# Models utilities
models-build: ## Build/generate model files from JSON sources
	@echo "Generating models..."
	$(UV) run python -m utils.models.build_models

models-maintenance: ## Run the models maintenance script
	@echo "Models maintenance..."
	$(UV) run python -m utils.models.maintenance

# Dataset utilities
dataset-export: ## Export datasets to HuggingFace (requires HF_PUSH_DATASET_KEY and DATABASE_URI)
	@echo "Exporting datasets..."
	@if [ -z "$$DATABASE_URI" ]; then \
		echo "Error: DATABASE_URI is not defined"; \
		exit 1; \
	fi
	@if [ -z "$$HF_PUSH_DATASET_KEY" ]; then \
		echo "Error: HF_PUSH_DATASET_KEY is not defined"; \
		exit 1; \
	fi
	$(UV) run python utils/export_dataset.py

# Ranking methods (Poetry subproject)
ranking-install: ## Install ranking_methods project dependencies (via Poetry)
	@echo "Installing ranking_methods project dependencies..."
	cd utils/ranking_methods && poetry install

ranking-test: ## Run ranking_methods project tests
	@echo "Testing ranking_methods project..."
	cd utils/ranking_methods && poetry run pytest tests/

compute-rankings: ## Execute the ranking pipeline (see notebooks for more options)
	@echo "To use the ranking pipeline, see:"
	@echo "  - utils/ranking_methods/notebooks/pipeline.ipynb"
	@echo "  - utils/ranking_methods/notebooks/rankers.ipynb"
	@echo "  - utils/ranking_methods/notebooks/frugal.ipynb"
	@echo "  - utils/ranking_methods/notebooks/graph.ipynb"
	
	@echo "Compute rankings..."
	$(UV) run python -m utils.models.build_simplified_llm_list_ranking
	cd utils/ranking_methods/src && poetry run python -m rank_comparia.export
	cp utils/ranking_methods/src/output/ml_final_data.json utils/models/generated-models-extra-data.json
	@$(MAKE) models-build

# Cleanup
clean: ## Clean generated files
	@echo "Cleaning..."
	rm -rf frontend/node_modules
	rm -rf frontend/.svelte-kit
	rm -rf frontend/build
	rm -rf .venv
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	cd utils/ranking_methods && poetry env remove --all 2>/dev/null || true

check-requirements: ## Check that required tools are installed
	@echo "Checking prerequisites..."
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "Python 3 is required but not installed."; exit 1; }
	@command -v $(NPM) >/dev/null 2>&1 || { echo "npm is required but not installed."; exit 1; }
	@command -v $(UV) >/dev/null 2>&1 || { echo "uv is not installed. Run 'make install-backend' to install it."; }
	@echo "All prerequisites are installed ✓"