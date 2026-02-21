# Contributing to Compar:IA

Thanks for your interest in contributing! This guide covers everything you need to get the project running locally and start contributing.

## Getting started

### Prerequisites

- Python 3.13+
- Node.js + yarn
- [uv](https://docs.astral.sh/uv/) (installed automatically by `make install-backend` if missing)

### Environment setup

```bash
cp .env.example .env
```

For real LLM calls, set `OPENROUTER_API_KEY` in your `.env`. To skip API calls entirely, uncomment `MOCK_RESPONSE=true` instead.

### With Docker

`make docker-app-up`

### Without Docker

#### Quick start with `make`

The easiest way to run Compar:IA is using the provided Makefile:

```bash
# Install all dependencies (backend + frontend)
make install

# Run both backend and frontend in development mode
make dev
```

This will start:

- Backend (FastAPI) on http://localhost:8001
- Frontend (SvelteKit) on http://localhost:5173

### Manual setup

**Backend:**

1. Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Install dependencies: `uv sync`
3. Run the server: `uv run uvicorn backend.main:app --reload --timeout-graceful-shutdown 1 --port 8001`

**Frontend:**

1. Install Node.js and yarn
2. Navigate to frontend: `cd frontend/`
3. Install dependencies: `yarn install`
4. Run dev server: `yarn run dev`

**(optional) Dashboard:**

```bash
uv run uvicorn controller:app --reload --port 21001
```

### Testing

```bash
# Frontend unit tests
cd frontend && npx vitest --run

# Frontend E2E tests (requires build first)
cd frontend && yarn run build && npx playwright test

# Lint & type check
cd frontend && yarn run lint
cd frontend && yarn run check
```

No backend test suite exists currently.

---

## Available Makefile commands

```bash
make help                  # Display all available commands
make install               # Install all dependencies
make install-backend       # Install backend dependencies only
make install-frontend      # Install frontend dependencies only
make dev                   # Run backend + frontend (parallel)
make dev-full              # Run backend + frontend with Postgres and Redis
make dev-backend           # Run backend only
make dev-frontend          # Run frontend only
make dev-controller        # Run the dashboard controller
make build-frontend        # Build frontend for production
make clean                 # Clean generated files
make check-requirements    # Check that required tools are installed

make lint-python           # Check python code (mypy)
make lint-frontend         # Check frontend code
make format-python         # Format python code
make format-frontend       # Format frontend code

make db-generate-init      # Generate docker/data/init-db.sql from schema files
make redis                 # Launch Redis using docker compose

make docker-app-up         # Launch full app in Docker (frontend + backend + infra)
make docker-app-down       # Stop only app services, keep infra
make docker-app-logs       # Show logs for frontend and backend containers

make models-build          # Generates model files from JSON sources
make models-maintenance    # Launches the model maintenance script
make models-doc            # Build/generate LLM doc and JSON schemas

make compute-rankings      # Execute the ranking pipeline
make ranking-install       # Install ranking_methods project dependencies
make ranking-test          # Run ranking_methods project tests

make dataset-export        # Exports datasets to HuggingFace

make i18n-clean-locales        # Remove unused locale keys
make i18n-build-suggestions    # Generate prompt suggestion translations
make i18n-build-news           # Generate news files
```

---

## Database

**Prerequisites:** `COMPARIA_DB_URI` environment variable configured (defaults to `postgresql://postgres:postgres@localhost:5432/languia` for local dev)

```bash
# Generate init-db.sql and start Postgres via Docker
make db-generate-init

# Or start the full dev stack with Postgres + Redis
make dev-full
```

---

## Models

These commands generate [`utils/models/generated-models.json`](utils/models/generated-models.json) and update translations in [`frontend/locales/messages/fr.json`](frontend/locales/messages/fr.json).

```bash
make models-build          # Generate model files from JSON sources
make models-maintenance    # Run model health checks
```

---

## Datasets

**Prerequisites:** `COMPARIA_DB_URI` and `HF_PUSH_DATASET_KEY` environment variables configured

```bash
# Export datasets to HuggingFace
uv run python utils/export_dataset.py
```

---

## Ranking methods

```bash
# Install ranking_methods project dependencies (via Poetry)
make ranking-install
```

For more details, consult [`utils/ranking_methods/README.md`](utils/ranking_methods/README.md) and the notebooks in [`utils/ranking_methods/notebooks/`](utils/ranking_methods/notebooks/).

---

## Translating the platform

The frontend uses [@inlang/paraglide-js](https://inlang.com/m/gerre34r/library-inlang-paraglideJs) for i18n. Currently supported locales: **fr** (default), **da**, **en**, **lt**, **sv**.

Translation files live in `frontend/locales/messages/`. To add a new language, create a new JSON file following the structure of `fr.json` and register the locale in the paraglide config.

---

## Architecture

- `frontend/`: SvelteKit frontend (Vite, TailwindCSS, French Design System). Runs on port 5173.
- `backend/main.py`: FastAPI entry point. Runs on port 8001.
- `languia/`: Backend logic (streaming, voting, reveal, rate limiting, persistence).
- `docker/`: Docker Compose configs (infra + app overlay).
- `utils/`: Model generation, ranking methods, database schemas, dataset export.
- `controller.py`: Simple error monitoring dashboard (`uv run uvicorn controller:app --reload --port 21001`).
- `templates/`: Jinja2 templates for the dashboard.
