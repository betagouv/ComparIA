.PHONY: help install install-backend install-frontend dev dev-redis dev-backend dev-frontend dev-controller build-frontend db-generate-init db  db-prd-local docker-app-up docker-app-down docker-app-logs clean redis models-doc up-fr down-fr logs-fr up-da down-da logs-da dataset-export-fr

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

KEEPASS_DB ?= $(HOME)/comparia.kdbx
KEEPASS_GROUP_FR ?= comparia/instances/fr
KEEPASS_GROUP_DA ?= comparia/instances/da

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
db-generate-init: ## Generate devops/db-init/init-db.sql from schema files
	@bash devops/db-init/generate-init-db.sh

## Launch and init Postgres database using docker compose
db:
	@$(MAKE) db-generate-init
	@echo "Starting PostgreSQL database..."
	docker compose -f devops/instances/db-redis/docker-compose.yml up postgres -d

redis: ## Launch Redis using docker compose
	@echo "Starting Redis..."
	docker compose -f devops/instances/db-redis/docker-compose.yml up redis -d

up-fr: ## Launch FR instance (frontend + backend + postgres + redis)
	@$(MAKE) db-generate-init
	eval $$(uv run --group devops python devops/keepassxc/load_env.py --db $(KEEPASS_DB) --group "$(KEEPASS_GROUP_FR)") && docker compose -f devops/instances/fr/app.compose.fr.yml up -d --build

down-fr: ## Stop FR instance
	docker compose -f devops/instances/fr/app.compose.fr.yml down

logs-fr: ## Show logs for FR instance
	docker compose -f devops/instances/fr/app.compose.fr.yml logs -f

up-da: ## Launch DA instance (frontend + backend + postgres + redis)
	@$(MAKE) db-generate-init
	eval $$(uv run --group devops python devops/keepassxc/load_env.py --db $(KEEPASS_DB) --group "$(KEEPASS_GROUP_DA)") && docker compose -f devops/instances/da/app.compose.da.yml up -d --build

down-da: ## Stop DA instance
	docker compose -f devops/instances/da/app.compose.da.yml down

logs-da: ## Show logs for DA instance
	docker compose -f devops/instances/da/app.compose.da.yml logs -f

dataset-export-fr: ## Export FR datasets to HuggingFace (requires HF_PUSH_DATASET_KEY and COMPARIA_DB_URI)
	@echo "Exporting datasets..."
	@if [ -z "$$COMPARIA_DB_URI" ]; then \
		echo "Error: COMPARIA_DB_URI is not defined"; \
		exit 1; \
	fi
	@if [ -z "$$HF_PUSH_DATASET_KEY" ]; then \
		echo "Error: HF_PUSH_DATASET_KEY is not defined"; \
		exit 1; \
	fi
	$(UV) run python -m utils.dataset.run fr

docker-app-up: ## Launch full app in Docker (frontend + backend + infra)
	@$(MAKE) db-generate-init
	@echo "Starting full app with Docker..."
	docker compose -f devops/instances/db-redis/docker-compose.yml -f devops/docker/app.compose.override.yml up -d --build

docker-app-down: ## Stop only app services (frontend + backend), keep infra
	@echo "Stopping app services..."
	docker compose -f devops/instances/db-redis/docker-compose.yml -f devops/docker/app.compose.override.yml rm -sf frontend backend

docker-app-logs: ## Show logs for frontend and backend containers
	docker compose -f devops/instances/db-redis/docker-compose.yml -f devops/docker/app.compose.override.yml logs -f frontend backend

dev-full: ## Launch backend and frontend with Postgres and Redis (Ctrl+C to stop)
	@echo "Launching compar:IA with Postgres and Redis..."
	@echo "Starting Redis..."
	@docker compose -f devops/instances/db-redis/docker-compose.yml up redis -d || echo "Redis already running or failed to start"
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
	$(UV) run uvicorn backend.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT) --timeout-graceful-shutdown 1

dev-frontend: ## Launch only the frontend (Vite + SvelteKit)
	@echo "Starting frontend on port $(FRONTEND_PORT)..."
	cd frontend && $(NPM) run dev

dev-controller: ## Launch the dashboard controller
	@echo "Starting controller on port $(CONTROLLER_PORT)..."
	$(UV) run uvicorn controller:app --reload --host 0.0.0.0 --port $(CONTROLLER_PORT)

build-frontend: ## Build the frontend for production
	@echo "Building frontend..."
	cd frontend && $(NPM) run build

lint-python: ## Check python code
	@echo "Checking python code..."
	uv run mypy .

lint-frontend: ## Check frontend code
	@echo "Checking frontend code..."
	cd frontend && $(NPM) run lint

format-python: ## Format python code
	@echo "Formatting python code..."
	uv run autoflake .
	uv run isort .
	uv run black .

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
	@docker compose -f devops/instances/db-redis/docker-compose.yml down -v
	@$(MAKE) dev-full

# Models utilities
models-build: ## Build/generate model files from JSON sources
	@echo "Generating models..."
	$(UV) run python -m utils.models.build_models

models-maintenance: ## Run the models maintenance script
	@echo "Models maintenance..."
	$(UV) run python -m utils.models.maintenance

models-doc: ## Build/generate llm doc and JSON schemas
	@echo "Generating LLM specs documentation and JSON schemas..."
	$(UV) run python -m utils.models.schemas.build_doc

# Dataset utilities
dataset-export: ## Export FR datasets to HuggingFace (requires HF_PUSH_DATASET_KEY and COMPARIA_DB_URI)
	@echo "Exporting datasets..."
	@if [ -z "$$COMPARIA_DB_URI" ]; then \
		echo "Error: COMPARIA_DB_URI is not defined"; \
		exit 1; \
	fi
	@if [ -z "$$HF_PUSH_DATASET_KEY" ]; then \
		echo "Error: HF_PUSH_DATASET_KEY is not defined"; \
		exit 1; \
	fi
	$(UV) run python -m utils.dataset.run fr

dataset-export-da: ## Export DA datasets to HuggingFace (requires HF_PUSH_DATASET_KEY_DA and COMPARIA_DB_URI)
	@echo "Exporting datasets..."
	@if [ -z "$$COMPARIA_DB_URI" ]; then \
		echo "Error: COMPARIA_DB_URI is not defined"; \
		exit 1; \
	fi
	@if [ -z "$$HF_PUSH_DATASET_KEY_DA" ]; then \
		echo "Error: HF_PUSH_DATASET_KEY_DA is not defined"; \
		exit 1; \
	fi
	$(UV) run python -m utils.dataset.run da

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
	$(UV) run python -m utils.ranking.run

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



###### Old


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
