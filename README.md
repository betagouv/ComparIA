<br>
<p align="center">
  <a href="https://comparia.beta.gouv.fr/">
  <img src="https://github.com/user-attachments/assets/bd071ffd-1253-486d-ad18-9f5b371788b0" width=300px alt="compar:IA logo" />  </a>
</p>


<h2 align="center" >Comparateur d’IA conversationnelles / Conversational AI comparator</h3>
<p align="center">Compar:IA est un outil permettant de comparer à l’aveugle différents modèles d'IA conversationnelle pour sensibiliser aux enjeux de l'IA générative (biais, impact environmental) et constituer des jeux de données de préférence en français.</p>
<p align="center">Compar:IA is a tool for blindly comparing different conversational AI models to raise awareness about the challenges of generative AI (bias, environmental impact) and to build up French-language preference datasets.</p>

<p align="center"><a href="https://comparia.beta.gouv.fr/">🌐 comparia.beta.gouv.fr</a> · <a href="https://www.comparia.beta.gouv.fr/a-propos">📚 À propos</a> · <a href="https://beta.gouv.fr/startups/languia.html">🚀 Description de la startup d'Etat</a><p>
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

<br>

Le comparateur est basé sur [Gradio](https://www.gradio.app/) et [FastChat](https://github.com/lm-sys/FastChat/), le code de l'arène Chatbot Arena par LMSYS (voir [Project architecture and rationale (en)](https://github.com/betagouv/ComparIA?tab=readme-ov-file#project-architecture-and-rationale) plus bas).

The comparator is based on [Gradio](https://www.gradio.app/) and [FastChat](https://github.com/lm-sys/FastChat/), the Chatbot Arena code by LMSYS (see [Project architecture and rationale](https://github.com/betagouv/ComparIA?tab=readme-ov-file#project-architecture-and-rationale) below).



## Run the arena

1. Rename `register-api-endpoint-file.json.dist` to `register-api-endpoint-file.json` and add valid API keys

### Without Docker

Due to how Gradio's Custom Components work and because they haven't been published as Python packages, building them manually is a bit tedious. At the moment we use 4 custom components: 

```bash
pip install -r requirements.txt
gradio cc install custom_components/frinput
gradio cc build --no-generate-docs custom_components/frinput
gradio cc install custom_components/customradiocard;gradio cc build --no-generate-docs custom_components/customradiocard
gradio cc install custom_components/customdropdown;gradio cc build --no-generate-docs custom_components/customdropdown
gradio cc install custom_components/customchatbot; npm install @gouvfr/dsfr;
gradio cc build --no-generate-docs custom_components/customchatbot
```
then `export LANGUIA_DEBUG=True; uvicorn main:app --reload --timeout-graceful-shutdown 1` or simply `uvicorn main:app`
For arena only, you can also launch: `gradio demo.py`

#### To dev for a custom component

You can launch this to work on the first custom component (first screen):
`gradio cc dev --component-directory custom_components/customdropdown demo.py`

### With Docker

`cd docker/; docker compose up -d`

For image building only you can use: `docker build -t comparia . -f docker/Dockerfile`

## Project architecture and rationale

### LMSys fork
We initially forked LMSYS' FastChat codebase, used at https://lmarena.ai to get an immediately running arena. Its architecture was composed of:
- the arena (a Gradio project with 2-3 Python files)
- a controller to register model workers

But as it was easier to run models in vLLM Docker containers or by using external APIs, the controller / model workers architecture ended up being unused code. Furthermore, we needed a dashboard for the controller so it got recoded.

### Custom Components
Our main focus with compar:IA is to invest heavily on overall design and UX/UI. Thanks to Gradio's [Custom Components](https://www.gradio.app/guides/custom-components-in-five-minutes) we can customize any Gradio component as a Svelte app, and control the user interface look and feel.

We currently use 4 distinct (and sometimes poorly named) Custom Components:
- `FrInput`: the [DSFR](https://www.systeme-de-design.gouv.fr/) input component
- `CustomDropdown`: encompasses most of the first screen, with mode selection, models selection, and initial textarea
- `CustomRadioCard`: used in the first screen for suggestions and later for voting
- `CustomChatbot`: a component crafted for the specific compar:IA experience, allowing you to compare two chatbots' response to one user message, and receive user's feedback



### Mounted `gradio.Blocks` within a FastAPI app

Because we needed a static website as well, we used Gradio's [`mount_gradio_app`](https://www.gradio.app/docs/gradio/mount_gradio_app`) feature, allowing you to customize how FastAPI serves the gradio app (Gradio is based on FastAPI), while using the underlying FastAPI app to serve other pages. This lives in `main.py` while most of the Gradio code is split between `languia/block_arena.py` and `languia/listeners.py`.
The static site's pages are in the `templates/` folder, which also hosts the complex Jinja2 template files needed in the arena (especially after the "reveal" step).

### Future evolutions

After 8 months of intensive development, the Gradio framework may show some limits, especially when it comes to fully custom CSS. Ugly CSS overrides are used heavily throughout this repo (especially in the infamous `assets/custom-arena.css`), while the integration of the French design system (DSFR) is made difficult by how Gradio adds a lot of Svelte-generated CSS everywhere.
Furthermore, since the app is now more stable, we don't need to iterate quickly anymore, which is what Gradio allowed, and we could gain some snappiness by using a Svelte SPA (Single Page App) and a lighter frontend-backend communication.
I feel there is a gradual path consisting in decapsulating the Custom Components one by one into a basic Svelte app, and replace Gradio with a basic FastAPI endpoint, screen-by-screen and iterating. If you have opinions on this, I warmly welcome you to open an issue on the matter 🙃
