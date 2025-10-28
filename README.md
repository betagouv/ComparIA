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

### With Docker Compose

`docker compose -f docker/docker-compose.yml up backend frontend`

### Back-end
1. Install `uv`
2. `uv sync`
3. `uv run uvicorn main:app --reload --timeout-graceful-shutdown 1` or simply `uvicorn main:app`

### Front-end
1. Install `npx`
2. `cd frontend/; npx vite dev`

## Project architecture and rationale
### Architecture

- `frontend/`: main code for frontend.
Frontend is Sveltekit. It lives in `frontend/` and runs on port 5173 in dev env, which is Vite's default.

- `main.py`: the Python file for the main FastAPI app
- `languia`: backend code.
Most of the Gradio code is split between `languia/block_arena.py` and `languia/listeners.py`. It runs on port 8000 by default. Backend is a mounted `gradio.Blocks` within a FastAPI app.
- `demo.py`: the Python file for Gradio's `gr.Blocks` configuration

- `docker/`: Docker config
- `utils/`: utilities for dataset handling and database manipulation

- `controller.py`: a simplistic dashboard
You can run it with FastAPI: `uv run uvicorn controller:app --reload --port 21001`
- `templates`: Jinja2 template for the dashboard

- `pyproject.toml`: Python requirements
- `sonar-project.properties` SonarQube configuration

### Evolution
We want to get rid of that Gradio code by transforming it into async FastAPI code and Redis session handling.