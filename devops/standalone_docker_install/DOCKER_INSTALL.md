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

| Variable | Description |
|---|---|
| `PUBLIC_DOMAIN` | Your domain name, e.g. `comparia.example.com` |
| `PUBLIC_URL` | Full public URL, e.g. `https://comparia.example.com` |
| `POSTGRES_PASSWORD` | A strong password for the database |
| `OPENROUTER_API_KEY` | API key from [openrouter.ai](https://openrouter.ai) |

**3. Generate the database init file**

```bash
bash devops/generate-init-db.sh
```

**4. Start the stack**

```bash
docker compose -f devops/standalone_docker_install/docker-compose.yml --env-file devops/standalone_docker_install/.env up -d
```

Caddy will automatically obtain a TLS certificate for your domain on first startup. Make sure ports 80 and 443 are open on your server.

## Architecture

```
internet → Caddy (80/443, TLS) → frontend (SSR, port 3000)
                               → backend  (FastAPI, port 80)  → PostgreSQL
                                                               → Redis
```

## Updating

```bash
docker compose -f devops/standalone_docker_install/docker-compose.yml --env-file devops/standalone_docker_install/.env pull
docker compose -f devops/standalone_docker_install/docker-compose.yml --env-file devops/standalone_docker_install/.env up -d --build
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
python -m utils.models.build_models
```

Then rebuild the backend image.

## Contact

For questions or support: [contact@comparia.beta.gouv.fr](mailto:contact@comparia.beta.gouv.fr)
