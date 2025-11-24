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
    "http://localhost:8000"]

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

@app.get("/counter", response_class=JSONResponse)
async def counter(
    request: Request,
    c: str | None = None,
):
    # Get hostname from request headers
    hostname = request.client.host
    
    # Check if we should use country portal count based on hostname or query parameter
    country_portal = request.query_params.get("c")
    
    if hostname == "ai-arenaen.dk" or country_portal == "da":
        count = get_country_portal_count('da')
        objective = config.OBJECTIVES.get("da")
    else:
        count = get_country_portal_count('fr')
        objective = config.OBJECTIVES.get("fr")
    
    return JSONResponse(
        {
            "count": count,
            "objective": objective,
        }
    )


app = SentryAsgiMiddleware(app)
