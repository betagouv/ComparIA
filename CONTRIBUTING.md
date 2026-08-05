# Contributing to Compar:IA

Thanks for your interest in contributing! This guide covers everything you need to get the project running locally and start contributing.

## Getting started

### Prerequisites

- Python 3.13+
- Node.js + yarn
- [uv](https://docs.astral.sh/uv/) (installed automatically by `make install-backend` if missing)

### Install dependencies

```bash
make install
```

---

## Running locally (without Docker)

Local dev uses env vars set manually. Postgres and Redis are started via Docker.

Copy the example env file and fill in the required values:

```bash
cp .env.example .env
```

Set `OPENROUTER_API_KEY` for real LLM calls, or uncomment `MOCK_RESPONSE=true` to skip them. For the DA instance, change `DEFAULT_COUNTRY_PORTAL=da` and point `COMPARIA_DB_URI` to the DA database.

Start Postgres and Redis, then run:

```bash
make db
make redis
source .env
make dev      # backend on :8008, frontend on :5173
```

For the DA instance, copy `.env.example` and set `DEFAULT_COUNTRY_PORTAL=da` and `COMPARIA_DB_URI` to the DA database before sourcing.

---

## Running with Docker (per instance)

Each instance has its own Docker Compose file. Secrets are loaded from KeePass automatically. A shared Postgres and Redis are started automatically.

```bash
make up-fr      # Start FR instance (backend + frontend + postgres + redis)
make down-fr    # Stop FR instance
make logs-fr    # Follow FR instance logs

make up-da      # Start DA instance
make down-da    # Stop DA instance
make logs-da    # Follow DA instance logs
```

These commands load secrets from a KeePass database (`~/comparia_dev.kdbx` by default). You can use the team's shared database or create your own — one entry per variable, in groups `instances/fr` or `instances/da`, with **username = variable name** and **password = value**. See `devops/instances/fr/.env.fr.example` and `devops/instances/da/.env.da.example` for the full variable list.

Override the database path with:

```bash
KEEPASS_DB=/path/to/other.kdbx make up-fr
```

To start only the shared infrastructure:

```bash
make db         # Start shared Postgres
make redis      # Start shared Redis
```

---

## Database

Default local URI (set in `.env.example`):

- FR: `postgresql://comparia:comparia@localhost:5432/comparia`

```bash
make db                # Start Postgres via Docker (creates the default comparia database)
make db-reset-data     # Wipe Postgres volumes and restart fresh
```

Schema is managed with [Alembic](https://alembic.sqlalchemy.org/). Migration scripts live in `utils/database/alembic/versions/`. `COMPARIA_DB_URI` must be exported before running any migration command.

First-time setup on a fresh database:

```bash
make db
source .env
make db-migrate        # applies all migrations, creates tables
```

After modifying a SQLModel in `utils/database/models/`:

```bash
make db-migrate-generate MSG="describe your change"
make db-migrate
```

```bash
make db-migrate-status   # show current migration revision
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

**Prerequisites:** `COMPARIA_DB_URI`, `HF_PUSH_DATASET_KEY`, and `HF_PUSH_DATASET_PATH` environment variables configured.

```bash
make dataset-export        # Export FR datasets to HuggingFace
make dataset-export-da     # Export DA datasets to HuggingFace
```

---

## Testing

```bash
# Frontend unit tests
cd frontend && npx vitest --run

# Frontend E2E tests (requires build first)
cd frontend && yarn run build && npx playwright test

# Lint & type check
cd frontend && yarn run lint
cd frontend && yarn run check
```

---

## Translating the platform

The frontend uses [@inlang/paraglide-js](https://inlang.com/m/gerre34r/library-inlang-paraglideJs) for i18n. Currently supported locales: **fr** (default), **da**, **en**, **lt**, **sv**.

Translation files live in `frontend/locales/messages/`. To add a new language, create a new JSON file following the structure of `fr.json` and register the locale in the paraglide config.

---

## Architecture

- `frontend/`: SvelteKit frontend (Vite, TailwindCSS, French Design System). Runs on port 5173.
- `backend/main.py`: FastAPI entry point. Runs on port 8008.
- `backend/arena/`: Core arena logic (streaming, voting, rate limiting, persistence).
- `devops/instances/`: Per-instance Docker Compose files and env examples (fr, da).
- `devops/instances/postgres/`: Shared Postgres compose and schema init.
- `devops/instances/redis/`: Shared Redis compose.
- `devops/keepassxc/`: KeePass env loader script.
- `utils/`: Model generation, database schemas, dataset export.
