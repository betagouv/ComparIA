.PHONY: help install install-backend install-frontend test test-backend test-frontend test-dataset dev dev-redis dev-backend dev-frontend build-frontend db-generate-init-old db db-prd-local docker-app-up docker-app-down docker-app-logs clean redis models-doc up-fr down-fr logs-fr display-env-fr up-da down-da logs-da display-env-da dataset-export dataset-export-dry-run

# Variables
PYTHON := python3
UV := uv
NPM := yarn
BACKEND_PORT := 8008
FRONTEND_PORT := 5173
CONTROLLER_PORT := 21001

COMPARIA_REDIS_HOST ?= localhost
export COMPARIA_REDIS_HOST

KEEPASS_DB ?= $(HOME)/comparia_dev.kdbx
KEEPASS_GROUP_FR ?= instances/fr
KEEPASS_GROUP_DA ?= instances/da

help: ## Display this help
	@echo "Available commands for compar:IA:"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'

###################################
# Shared - PostgreSQL and Redis init using docker
###################################

network: ## Create shared Docker network (idempotent)
	@docker network create comparia-net 2>/dev/null || true

db-generate-init-old: ## (legacy) Create comparia_da and apply old SQL schema to both databases via docker exec
	@bash devops/instances/postgres/generate-init-db.sh
	@docker compose -f devops/instances/postgres/postgres-simple.compose.yml exec -T postgres-simple \
		psql -U comparia -c "CREATE DATABASE comparia_da OWNER comparia;" 2>/dev/null || true
	@sed -e 's/"languia-dev"/"comparia"/g' -e 's/"languia-prd"/"comparia"/g' -e 's/"languia"/"comparia"/g' \
		devops/instances/postgres/schema.sql | \
		docker compose -f devops/instances/postgres/postgres-simple.compose.yml exec -T postgres-simple \
		psql -U comparia -d comparia
	@sed -e 's/"languia-dev"/"comparia"/g' -e 's/"languia-prd"/"comparia"/g' -e 's/"languia"/"comparia"/g' \
		devops/instances/postgres/schema.sql | \
		docker compose -f devops/instances/postgres/postgres-simple.compose.yml exec -T postgres-simple \
		psql -U comparia -d comparia_da

db: ## Launch Postgres database using docker compose (empty schema, use db-migrate to apply)
	@$(MAKE) network
	@echo "Starting PostgreSQL database..."
	docker compose -f devops/instances/postgres/postgres-simple.compose.yml up -d

db-reset-data:
	@echo "Removing docker dev data (volumes)..."
	@docker compose -f devops/instances/postgres/postgres-simple.compose.yml down -v

db-migrate: ## Apply pending Alembic migrations (requires COMPARIA_DB_URI)
	@if [ -z "$$COMPARIA_DB_URI" ]; then echo "Error: COMPARIA_DB_URI is not set"; exit 1; fi
	$(UV) run alembic upgrade head

db-migrate-generate: ## Generate a new Alembic migration (usage: make db-migrate-generate MSG="description", requires COMPARIA_DB_URI)
	@if [ -z "$$COMPARIA_DB_URI" ]; then echo "Error: COMPARIA_DB_URI is not set"; exit 1; fi
	$(UV) run alembic revision --autogenerate -m "$(MSG)"

db-migrate-status: ## Show current Alembic migration status (requires COMPARIA_DB_URI)
	@if [ -z "$$COMPARIA_DB_URI" ]; then echo "Error: COMPARIA_DB_URI is not set"; exit 1; fi
	$(UV) run alembic current

db-schema-dump: ## Dump current database schema (requires COMPARIA_DB_URI)
	@if [ -z "$$COMPARIA_DB_URI" ]; then echo "Error: COMPARIA_DB_URI is not set"; exit 1; fi
	pg_dump "$$COMPARIA_DB_URI" --schema-only --no-owner --no-privileges

db-seed-admins: ## Promote ADMIN_EMAILS users to admin role (requires COMPARIA_DB_URI)
	@if [ -z "$$COMPARIA_DB_URI" ]; then echo "Error: COMPARIA_DB_URI is not set"; exit 1; fi
	./comparia-cli db seed-admins

redis: ## Launch Redis using docker compose
	@$(MAKE) network
	@echo "Starting Redis..."
	docker compose -f devops/instances/redis/redis.compose.yml up -d

redis-down: ## Stop Redis
	docker compose -f devops/instances/redis/redis.compose.yml down


###################################
# Instance fr docker
###################################
up-fr: ## Launch FR instance (frontend + backend + postgres + redis)
	@$(MAKE) redis
	@$(MAKE) db
	eval $$(uv run --group devops python devops/keepassxc/load_env.py --db $(KEEPASS_DB) --group "$(KEEPASS_GROUP_FR)") && \
	docker compose -f devops/instances/fr/app.compose.fr.yml up -d --build

down-fr: ## Stop FR instance
	docker compose -f devops/instances/fr/app.compose.fr.yml down

logs-fr: ## Show logs for FR instance
	docker compose -f devops/instances/fr/app.compose.fr.yml logs -f

display-env-fr: ## Display env vars loaded from KeePass for FR instance
	uv run --group devops python devops/keepassxc/load_env.py --db $(KEEPASS_DB) --group "$(KEEPASS_GROUP_FR)" --mask

###################################
# Instance da docker
###################################

up-da: ## Launch DA instance (frontend + backend + postgres + redis)
	eval $$(uv run --group devops python devops/keepassxc/load_env.py --db $(KEEPASS_DB) --group "$(KEEPASS_GROUP_DA)") && \
	docker compose -f devops/instances/da/app.compose.da.yml up -d --build

down-da: ## Stop DA instance
	docker compose -f devops/instances/da/app.compose.da.yml down

logs-da: ## Show logs for DA instance
	docker compose -f devops/instances/da/app.compose.da.yml logs -f

display-env-da: ## Display env vars loaded from KeePass for DA instance
	uv run --group devops python devops/keepassxc/load_env.py --db $(KEEPASS_DB) --group "$(KEEPASS_GROUP_DA)" --mask

###################################
# Development with local code
###################################

test: test-backend test-frontend ## Run all tests

test-backend: ## Run the python test suite (no DB required)
	$(UV) run --group dev --group data pytest tests -q

test-frontend: ## Run the frontend unit tests
	cd frontend && yarn vitest run

test-dataset: ## Run dataset export tests (no DB required)
	$(UV) run --group data python tests/dataset/test_comparison_to_turns.py
	$(UV) run --group data python tests/dataset/test_streaming_export.py

install: install-backend install-frontend ## Install all dependencies (backend + frontend)

install-backend: ## Install Python backend dependencies with uv
	@echo "Installing backend dependencies..."
	@if ! command -v uv &> /dev/null; then \
		echo "uv is not installed. Installing..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi
	# ^ upstream's own installer, fetched over TLS; verifying its signature or
	# using a package manager (brew install uv, pipx install uv) is safer
	$(UV) sync

install-frontend: ## Install npm frontend dependencies
	@echo "Installing frontend dependencies..."
	cd frontend && $(NPM) install || npm install --legacy-peer-deps

dev: ## Launch backend and frontend (env vars must be exported, e.g. source .env)
	$(MAKE) -j 2 dev-backend dev-frontend

dev-backend: ## Launch only the backend (FastAPI + Gradio)
	@echo "Starting backend on port $(BACKEND_PORT)..."
	$(UV) run uvicorn backend.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT) --timeout-graceful-shutdown 1

dev-frontend: ## Launch only the frontend (Vite + SvelteKit)
	@echo "Starting frontend on port $(FRONTEND_PORT)..."
	cd frontend && $(NPM) run dev

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

check-requirements: ## Check that required tools are installed
	@echo "Checking prerequisites..."
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "Python 3 is required but not installed."; exit 1; }
	@command -v $(NPM) >/dev/null 2>&1 || { echo "npm is required but not installed."; exit 1; }
	@command -v $(UV) >/dev/null 2>&1 || { echo "uv is not installed. Run 'make install-backend' to install it."; }
	@echo "All prerequisites are installed ✓"

clean: ## Clean generated files
	@echo "Cleaning..."
	rm -rf frontend/node_modules
	rm -rf frontend/.svelte-kit
	rm -rf frontend/build
	rm -rf .venv
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

###################################
# i18n utilities
###################################
i18n-clean-locales: ## Remove locales keys not present in fr
	@echo "Cleaning frontend locales keys..."
	./comparia-cli internal i18n

###################################
# Dataset utilities
###################################
dataset-export: ## Export the datasets to the destinations set in the admin panel (requires COMPARIA_DB_URI)
	@echo "Exporting datasets..."
	@if [ -z "$$COMPARIA_DB_URI" ]; then \
		echo "Error: COMPARIA_DB_URI is not defined"; \
		exit 1; \
	fi
	$(UV) run python -m utils.dataset.run

dataset-export-dry-run: ## Build the datasets locally and send them nowhere (requires COMPARIA_DB_URI)
	@echo "Exporting datasets..."
	@if [ -z "$$COMPARIA_DB_URI" ]; then \
		echo "Error: COMPARIA_DB_URI is not defined"; \
		exit 1; \
	fi
	$(UV) run python -m utils.dataset.run --dry-run
