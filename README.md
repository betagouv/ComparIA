<br>
<p align="center">
  <a href="https://comparia.beta.gouv.fr/">
  <img src="https://github.com/user-attachments/assets/bd071ffd-1253-486d-ad18-9f5b371788b0" width=300px alt="compar:IA logo" />  </a>
</p>

<h2 align="center" >Comparateur d’IA conversationnelles / Conversational AI comparator</h3>
<p align="center">Compar:IA est un outil permettant de comparer à l’aveugle différents modèles d'IA conversationnelle pour sensibiliser aux enjeux de l'IA générative (biais, impact environmental) et constituer des jeux de données de préférence en français.</p>
<p align="center">Compar:IA is a tool for blindly comparing different conversational AI models to raise awareness about the challenges of generative AI (bias, environmental impact) and to build up French-language preference datasets.</p>

<p align="center"><a href="https://comparia.beta.gouv.fr/">🌐 comparia.beta.gouv.fr</a> · <a href="https://comparia.beta.gouv.fr/a-propos">📚 À propos</a> · <a href="https://beta.gouv.fr/startups/languia.html">🚀 Description de la startup d'Etat</a><p>
<div align="center">
  <a href="https://comparia.beta.gouv.fr/" 
     aria-label="Cliquez pour se rendre sur la plateforme hébergée"
     title="Capture d'écran du comparateur">
    <img 
      src="https://github.com/user-attachments/assets/6c8257fc-a2e5-4ee1-8052-dbf14a0419ea" 
      alt="Aperçu du comparateur" 
      width="800"
    />
  </a>
</div>
<div align="center">
  <sub>
    <i>Cliquez sur l'image ci-dessus pour consulter le site (s'ouvre dans un nouvel onglet)</i>
  </sub>
</div>

## Run the arena

### API configuration

We rely heavily on OpenRouter, so if you want to test with real providers, in your environment variables, you need to have `OPENROUTER_API_KEY` set according to the configured models located in `utils/models/generated_models.json`.

#### Mock Response Mode

For testing purposes, you can enable mock responses by setting the `MOCK_RESPONSE` environment variable to `true` in your `.env` file:

```bash
MOCK_RESPONSE=True
```


### Development and Testing

### With Docker

`docker compose -f docker/docker-compose.yml up backend frontend`

### Without Docker

#### Quick start with `make`

The easiest way to run Languia is using the provided Makefile:

```bash
# Install all dependencies (backend + frontend)
make install

# Run both backend and frontend in development mode
make dev
```

This will start:

- Backend (FastAPI + Gradio) on http://localhost:8001
- Frontend (SvelteKit) on http://localhost:5173

### Manual Setup

**Backend:**

1. Install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Install dependencies: `uv sync`
3. Run the server: `uv run uvicorn main:app --reload --timeout-graceful-shutdown 1 --port 8001`

**Frontend:**

1. Install Node.js and yarn
2. Navigate to frontend: `cd frontend/`
3. Install dependencies: `yarn install`
4. Run dev server: `vite dev` or `npm run dev` or `npx vite dev`

**(optional) Dashboard:**

```bash
uv run uvicorn controller:app --reload --port 21001
```

## Other operations

### Available Makefile Commands

```bash
make help                # Display all available commands
make install             # Install all dependencies
make install-backend     # Install backend dependencies only
make install-frontend    # Install frontend dependencies only
make dev                 # Run backend + frontend (parallel)
make dev-backend         # Run backend only
make dev-frontend        # Run frontend only
make dev-controller      # Run the dashboard controller
make build-frontend      # Build frontend for production
make test-backend        # Run backend tests
make test-frontend       # Run frontend tests
make clean               # Clean generated files

make db-schema-init   # Initializes the database schema
make db-migrate       # Applies migrations

make models-build       # Generates model files from JSON sources
make models-maintenance # Launches the model maintenance script

make dataset-export   # Exports datasets to HuggingFace

```

### Database

**Prerequisites:** `DATABASE_URI` environment variable configured

```bash
# Initialize database schema
psql $DATABASE_URI -f utils/schemas/conversations.sql
psql $DATABASE_URI -f utils/schemas/votes.sql
psql $DATABASE_URI -f utils/schemas/reactions.sql
psql $DATABASE_URI -f utils/schemas/logs.sql

# Apply database migrations
psql $DATABASE_URI -f utils/schemas/migrations/conversations_13102025.sql
psql $DATABASE_URI -f utils/schemas/migrations/reactions_13102025.sql
```

### Models

These commands generate [`utils/models/generated-models.json`](utils/models/generated-models.json) and update translations in [`frontend/locales/messages/fr.json`](frontend/locales/messages/fr.json).

```bash
# Generate model files from JSON sources
uv run python utils/models/build_models.py

# Run the models maintenance script
uv run python utils/models/maintenance.py
```

#### Mock responses

If you don't have access to an API, you can enable mock responses by uncommenting in `.env` file:
`MOCK_RESPONSE=True`

### Datasets

**Prerequisites:** `DATABASE_URI` and `HF_PUSH_DATASET_KEY` environment variables configured

```bash
# Export datasets to HuggingFace
uv run python utils/export_dataset.py
```

### Ranking Methods

```bash
# Install ranking_methods project dependencies (via uv)
cd utils/ranking_methods && uv pip install -e .

```

For more details, consult [`utils/ranking_methods/README.md`](utils/ranking_methods/README.md) and the notebooks in [`utils/ranking_methods/notebooks/`](utils/ranking_methods/notebooks/).

## Project architecture and rationale

### Architecture

- `frontend/`: main code for frontend.
  Frontend is Sveltekit. It lives in `frontend/` and runs on port 5173 in dev env, which is Vite's default.

- `main.py`: the Python file for the main FastAPI app
- `languia`: backend code.
  Most of the Gradio code is split between `languia/block_arena.py` and `languia/listeners.py` with `languia/config.py` for config.
  It runs on port 8001 by default. Backend is a mounted `gradio.Blocks` within a FastAPI app.

- `docker/`: Docker config
- `utils/`: utilities for models generation and maintenance, ranking methods (Elo, maximum likelihood), database schemas, and dataset export to HuggingFace

- `controller.py`: a simplistic dashboard
  You can run it with FastAPI: `uv run uvicorn controller:app --reload --port 21001`
- `templates`: Jinja2 template for the dashboard

- `pyproject.toml`: Python requirements
- `sonar-project.properties` SonarQube configuration

### Evolution

We want to get rid of that Gradio code by transforming it into async FastAPI code and Redis session handling.

<div align="center">

<br />
<a href="https://digitalpublicgoods.net/r/comparia" target="_blank" rel="noopener noreferrer"><img src="https://github.com/DPGAlliance/dpg-resources/blob/main/docs/assets/dpg-badge.png?raw=true" width="100" alt="Digital Public Goods Badge"></a>

</div>
