.PHONY: help install install-backend install-frontend dev dev-backend dev-frontend dev-controller build-frontend clean

# Variables
PYTHON := python3
UV := uv
NPM := yarn
BACKEND_PORT := 8000
FRONTEND_PORT := 5173
CONTROLLER_PORT := 21001

help: ## Display this help
	@echo "Available commands for compar:IA:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

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
	cd frontend && $(NPM) install

dev: ## Launch backend and frontend in parallel (Ctrl+C to stop)
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

preview-frontend: build-frontend ## Preview the frontend build
	@echo "Previewing frontend..."
	cd frontend && $(NPM) run preview

lint-frontend: ## Check frontend code
	@echo "Checking frontend code..."
	cd frontend && $(NPM) run lint

format-frontend: ## Format frontend code
	@echo "Formatting frontend code..."
	cd frontend && $(NPM) run format

# Database utilities
db-schema-init: ## Initialize database schema
	@echo "Initializing database schema..."
	@if [ -z "$$DATABASE_URI" ]; then \
		echo "Error: DATABASE_URI is not defined"; \
		exit 1; \
	fi
	@echo "Executing SQL scripts in utils/schemas/..."
	psql $$DATABASE_URI -f utils/schemas/conversations.sql
	psql $$DATABASE_URI -f utils/schemas/votes.sql
	psql $$DATABASE_URI -f utils/schemas/reactions.sql
	psql $$DATABASE_URI -f utils/schemas/logs.sql

db-migrate: ## Apply database migrations
	@echo "Applying migrations..."
	@if [ -z "$$DATABASE_URI" ]; then \
		echo "Error: DATABASE_URI is not defined"; \
		exit 1; \
	fi
	psql $$DATABASE_URI -f utils/schemas/migrations/conversations_13102025.sql
	psql $$DATABASE_URI -f utils/schemas/migrations/reactions_13102025.sql

# Models utilities
models-build: ## Build/generate model files from JSON sources
	@echo "Generating models..."
	$(UV) run python utils/models/build_models.py

models-maintenance: ## Run the models maintenance script
	@echo "Models maintenance..."
	$(UV) run python utils/models/maintenance.py

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

ranking-pipeline: ## Execute the ranking pipeline (see notebooks for more options)
	@echo "To use the ranking pipeline, see:"
	@echo "  - utils/ranking_methods/notebooks/pipeline.ipynb"
	@echo "  - utils/ranking_methods/notebooks/rankers.ipynb"
	@echo "  - utils/ranking_methods/notebooks/frugal.ipynb"
	@echo "  - utils/ranking_methods/notebooks/graph.ipynb"

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