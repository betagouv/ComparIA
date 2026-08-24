# Self-hosting ComparIA with Docker

This guide covers deploying a single-machine instance of ComparIA using Docker Compose and Caddy (automatic HTTPS).

## Prerequisites

- A server with a public IP address
- A domain name pointing to that server
- [Docker](https://docs.docker.com/engine/install/) and the Compose plugin installed

## Setup

**1. Clone the repository**

```bash
git clone https://github.com/betagouv/ComparIA.git
cd ComparIA
```

**2. Configure environment**

```bash
cp devops/standalone_docker_install/.env.example devops/standalone_docker_install/.env
```

Edit `.env` and fill in at minimum:

| Variable             | Description                                          |
| -------------------- | ---------------------------------------------------- |
| `PUBLIC_DOMAIN`      | Your domain name, e.g. `comparia.example.com`        |
| `PUBLIC_URL`         | Full public URL, e.g. `https://comparia.example.com` |
| `POSTGRES_PASSWORD`  | A strong password for the database                   |
| `REDIS_PASSWORD`     | A strong password for Redis                          |
| `OPENROUTER_API_KEY` | API key from [openrouter.ai](https://openrouter.ai)  |
| `ALTCHA_HMAC_KEY`    | A random secret key for spam protection              |

Generate random values for `POSTGRES_PASSWORD`, `REDIS_PASSWORD` and `ALTCHA_HMAC_KEY` with for example:

```bash
openssl rand -hex 32
```

**3. Configure and start the database** — see [Database configuration](#database-configuration) below.

**4. Start the full stack**

```bash
cd devops/standalone_docker_install/
docker compose --env-file .env up -d
```

Caddy will automatically obtain a TLS certificate for your domain on first startup. Make sure ports 80 and 443 are open on your server.

## Database configuration

The schema is applied with Alembic migrations, baked into the backend image (`alembic.ini`, `utils/database/alembic/`). There is no separate init-db.sql to generate.

### Option A: containerized PostgreSQL (default)

Start the database first and wait for it to be healthy before starting the rest:

```bash
cd devops/standalone_docker_install/
docker compose --env-file .env up -d postgres
docker compose --env-file .env logs -f postgres # wait for "database system is ready to accept connections"
```

Build the backend image and apply migrations against it:

```bash
docker compose --env-file .env build backend
docker compose --env-file .env run --rm backend uv run alembic upgrade head
```

Continue to start the full stack part...

### Option B: external PostgreSQL

If you have an existing PostgreSQL instance, set `COMPARIA_DB_URI` in your `.env`:

```
COMPARIA_DB_URI=postgresql://user:password@host:5432/dbname
```

Apply migrations against it the same way:

```bash
docker compose --env-file .env build backend
docker compose --env-file .env run --rm backend uv run alembic upgrade head
```

Then comment out the `postgres` service and its volume in `docker-compose.yml`:

```yaml
# postgres:
#   image: postgres:16
#   ...
```

Also remove the `postgres` healthcheck dependency from the `backend` service `depends_on` block.

Then start the stack normally:

```bash
cd devops/standalone_docker_install/
docker compose --env-file .env up -d
```

## Architecture

```
internet → Caddy (80/443, TLS) → frontend (SSR, port 3000)
                               → backend  (FastAPI, port 80)  → PostgreSQL
                                                               → Redis
```

## Updating the application

To rebuild and update the app after checking out a new version of the code from the current repository:

```bash
cd devops/standalone_docker_install/
docker compose --env-file .env pull
docker compose -f devops/standalone_docker_install/docker-compose.yml --env-file .env up -d --build
```

## Useful commands

```bash
# View logs
docker compose -f devops/standalone_docker_install/docker-compose.yml logs -f

# Stop
docker compose -f devops/standalone_docker_install/docker-compose.yml down

# Stop and remove all data (destructive)
docker compose -f devops/standalone_docker_install/docker-compose.yml down -v
```

## Models

By default ComparIA uses the models defined in `utils/models/generated-models.json`. To customize the model list, edit `utils/models/models.json` and run:

```bash
make models-build
```

Then rebuild the backend image.
