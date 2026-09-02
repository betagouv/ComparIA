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

Set `OPENROUTER_API_KEY` for real LLM calls, or uncomment `MOCK_RESPONSE=true` to skip them. Set it before your first `make db-migrate`: migrations copy it onto the OpenRouter endpoint row, and from then on the key belongs to that endpoint and is edited at `/admin/llms/endpoints`. For the DA instance, change `COMPARIA_INSTANCE_NAME=da` and point `COMPARIA_DB_URI` to the DA database.

Start Postgres and Redis, then run:

```bash
make db
make redis
source .env
make dev      # backend on :8008, frontend on :5173
```

For the DA instance, copy `.env.example` and set `COMPARIA_INSTANCE_NAME=da` and `COMPARIA_DB_URI` to the DA database before sourcing.

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

These commands load secrets from a KeePass database (`~/comparia_dev.kdbx` by default). You can use the team's shared database or create your own, with one entry per variable, in groups `instances/fr` or `instances/da`, with **username = variable name** and **password = value**. See `devops/instances/fr/.env.fr.example` and `devops/instances/da/.env.da.example` for the full variable list.

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

Models live in the database, not in a file. Add them at `/admin/llms` (see [the admin panel guide](docs/admin.md#llms)), or import a JSON file:

```bash
./comparia-cli llms import path/to/llms-data.json
./comparia-cli llms export      # writes the current catalogue to data/llms-data.json
```

---

## The CLI

`./comparia-cli` is the way in to everything that is not an HTTP request. Every command takes `--help`.

```bash
./comparia-cli generate rankings     # recompute the leaderboard
./comparia-cli generate datasets     # build and publish the datasets
./comparia-cli db --help             # migrations, archiving, admin seeding
./comparia-cli maintenance on        # put the instance behind a maintenance page
./comparia-cli llms --help           # import and export the model catalogue
./comparia-cli internal all          # regenerate frontend types and i18n schemas
```

It needs `COMPARIA_DB_URI`, so `source .env` first.

---

## Datasets

**Prerequisites:** `COMPARIA_DB_URI` configured, and at least one enabled destination in the admin panel. Add `--dry-run` to build the datasets locally and send them nowhere.

```bash
make dataset-export           # Send the datasets to the configured destinations
make dataset-export-dry-run   # Build them locally and send them nowhere
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

Translation files live in `frontend/locales/messages/`. There are more files there than there are supported locales, because a language only counts once it appears in two lists, which have to agree:

- `locales` in `frontend/comparia.inlang/settings.json`
- `SUPPORTED_LOCALES` in `utils/database/models/app_settings.py`

To add one: copy `fr.json`, translate it, add the code to both lists, then enable it for your instance at `/admin/locales`.

---

## Architecture

- `frontend/`: SvelteKit frontend (Vite, TailwindCSS, French Design System). Runs on port 5173.
- `backend/main.py`: FastAPI entry point. Runs on port 8008.
- `backend/arena/`: Core arena logic (streaming, voting, rate limiting, persistence).
- `devops/instances/`: Per-instance Docker Compose files and env examples (fr, da).
- `devops/instances/postgres/`: Shared Postgres compose and schema init.
- `devops/instances/redis/`: Shared Redis compose.
- `devops/keepassxc/`: KeePass env loader script.
- `utils/`: Database models and migrations, the model catalogue, dataset export, ranking.
- `internal/`: Code generation for frontend types and i18n schemas.
- `docs/`: [Self-hosting](docs/self-hosting.md) and [the admin panel](docs/admin.md).

Almost all runtime configuration lives in the admin panel rather than in code or `.env`: models, languages, branding, legal pages, dataset destinations.
