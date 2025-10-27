from fastapi import FastAPI
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

from languia.utils import get_gauge_count

objective = config.OBJECTIVE


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


@app.get("/counter", response_class=JSONResponse)
async def counter():
    return JSONResponse({"count": get_gauge_count(), "objective": config.OBJECTIVE})


app = SentryAsgiMiddleware(app)
