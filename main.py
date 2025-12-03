from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from languia.block_arena import demo

import gradio as gr

from languia import config

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://localhost:8001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


demo = demo.queue(
    max_size=None,
    default_concurrency_limit=None,
    # default_concurrency_limit=40,
    # status_update_rate="auto",
    api_open=False,
)
# Should enable queue w/ mount_gradio_app: https://github.com/gradio-app/gradio/issues/8839
demo.run_startup_events()

app = gr.mount_gradio_app(
    app,
    demo,
    path="/api",
    root_path="/api",
    # allowed_paths=[config.assets_absolute_path],
    show_error=config.debug,
)

from languia.utils import get_country_portal_count


@app.get("/", response_class=JSONResponse)
@app.get("/available_models", response_class=JSONResponse)
@app.get("/models", response_class=JSONResponse)
async def available_models():
    return JSONResponse(
        {
            "models": [
                model
                for model in config.all_models_data["models"].values()
                if model["status"] in ("enabled", "archived")
            ],
            "data_timestamp": config.all_models_data["timestamp"],
        }
    )


# @app.get("/enabled_models", response_class=JSONResponse)
# async def enabled_models():
#     return JSONResponse(dict(config.models))

from fastapi import Query
from typing import Annotated, Optional

from languia.models import CohortRequest

@app.get("/counter", response_class=JSONResponse)
async def counter(
    request: Request,
    c: str | None = None,
):
    # don't get it from host
    # hostname = request.headers.get("Host")
    # Always check the query parameter 'c' for locale
    country_portal = request.query_params.get(
        "c", "fr"
    )  # Default to "fr" if not provided

    # Only allow "da" or "fr" as valid locales
    if country_portal not in ("da", "fr"):
        country_portal = "fr"  # Default to "fr" for invalid values

    if country_portal == "da":
        count = get_country_portal_count("da")
        objective = config.OBJECTIVES.get("da")
    else:  # country_portal == "fr"
        count = get_country_portal_count("fr")
        objective = config.OBJECTIVES.get("fr")

    return JSONResponse(
        {
            "count": count,
            "objective": objective,
        }
    )


@app.post("/cohorts", response_class=JSONResponse)
async def set_cohorts(request: CohortRequest):
    """
    Route pour définir la cohorte de ne pas suivre pour une session.

    Args:
        request: La requête FastAPI
        session_hash: Identifiant unique de la session
        cohort: Nom de la cohorte (par défaut "do-not-track")

    Returns:
        JSONResponse: Statut du suivi de cohorte
    """
    from languia.session import set_do_not_track

    if not request.session_hash:
        return JSONResponse(
            {
                "success": False,
                "error": "session_hash is required",
                "tracking_info": None,
            },
            status_code=400,
        )

    # Définir le suivi de cohorte
    success = set_do_not_track(request.session_hash, ",".join(request.cohorts))

    # Vérifier le statut actuel
    # tracking_info = get_do_not_track(session_hash)

    return JSONResponse(
        {
            "success": success,
            "session_hash": request.session_hash,
            "tracking_info": ",".join(request.cohorts),
        }
    )


app = SentryAsgiMiddleware(app)
