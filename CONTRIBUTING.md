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

There are two ways to load environment variables: manually (basic) or via KeePass (recommended for team members).

### Option A: manual env setup

Copy the example env file and fill in the required values:

```bash
cp .env.example .env
```

Set `OPENROUTER_API_KEY` for real LLM calls, or uncomment `MOCK_RESPONSE=true` to skip them. For the DA instance, change `DEFAULT_COUNTRY_PORTAL=da`, `DEFAULT_LOCALE=da`, and point `COMPARIA_DB_URI` to the DA database.

Then start backend and frontend manually:

```bash
source .env
make dev-backend   # FastAPI on http://localhost:8008
make dev-frontend  # SvelteKit on http://localhost:5173
```

### Option B: KeePass (recommended)

The KeePass integration loads env vars from a `.kdbx` database and runs backend + frontend in parallel:

```bash
make dev       # FR instance (loads instances/fr group from KeePass)
make dev-da    # DA instance (loads instances/da group from KeePass)
```

The database path defaults to `~/comparia_dev.kdbx`. Override with:

```bash
KEEPASS_DB=/path/to/other.kdbx make dev
```

You can use the team's shared database or create your own. The expected structure is one entry per variable, inside groups `instances/fr` or `instances/da`, with **username = variable name** and **password = value**.

See `devops/instances/fr/.env.fr.example` and `devops/instances/da/.env.da.example` for the full list of variables per instance.

---

## Running with Docker (per instance)

Each instance has its own Docker Compose file. A shared Postgres and Redis are started automatically.

```bash
make up-fr      # Start FR instance (backend + frontend + postgres + redis)
make down-fr    # Stop FR instance
make logs-fr    # Follow FR instance logs

make up-da      # Start DA instance
make down-da    # Stop DA instance
make logs-da    # Follow DA instance logs
```

These commands use KeePass to load secrets. To start only the shared infrastructure:

```bash
make db         # Start shared Postgres
make redis      # Start shared Redis
```

---

## Database

Default local URIs (used by `make dev` / `make dev-da`):

- FR: `postgresql://comparia:comparia@localhost:5432/comparia`
- DA: `postgresql://comparia:comparia@localhost:5432/comparia_da`

```bash
make db                # Start Postgres via Docker (creates both databases)
make db-reset-data     # Wipe Postgres volumes and restart fresh
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
