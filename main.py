import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from starlette.exceptions import HTTPException as StarletteHTTPException

import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from languia.gradio_web_server import demo
import logging
import gradio as gr

from languia import config

app = FastAPI()

app.mount("/assets", StaticFiles(directory="assets"), name="assets")

templates = Jinja2Templates(directory="templates")

if os.getenv("SENTRY_DSN"):
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    if os.getenv("SENTRY_SAMPLE_RATE"):
        traces_sample_rate = float(os.getenv("SENTRY_SAMPLE_RATE"))
    else:
        traces_sample_rate = 0.2
    logging.info("Sentry loaded with traces_sample_rate=" + str(traces_sample_rate))
    if os.getenv("SENTRY_ENV"):
        sentry_env = os.getenv("SENTRY_ENV")
    else:
        sentry_env = "development"
        sentry_sdk.init(
            dsn=os.getenv("SENTRY_DSN"),
            environment=sentry_env,
            traces_sample_rate=traces_sample_rate,
        )

env_debug = os.getenv("LANGUIA_DEBUG")

if env_debug:
    if env_debug.lower() == "true":
        debug = True
    else:
        debug = False
else:
    debug = False


if not debug:
    assets_absolute_path = "/app/assets"
else:
    assets_absolute_path = os.path.dirname(__file__) + "/assets"

# TODO: use gr.set_static_paths(paths=["test/test_files/"])?
gr.set_static_paths(paths=["assets/"])
# Note: access via e.g. DOMAIN/file=assets/fonts/Marianne-Bold.woff
logging.info("Allowing assets absolute path: " + assets_absolute_path)

# Set authorization credentials
auth = None

# TODO: Re-enable / Fine-tune for performance https://www.gradio.app/guides/setting-up-a-demo-for-maximum-performance
demo = demo.queue(
    default_concurrency_limit=10,
    status_update_rate=10,
    api_open=False,
)

app = gr.mount_gradio_app(
    app,
    demo,
    path="/arene",
    allowed_paths=[assets_absolute_path],
)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "config": config}
    )


from fastchat.model.model_registry import get_model_info

models_info = [get_model_info(model) for model in config.models]


@app.get("/modeles", response_class=HTMLResponse)
async def models(request: Request):
    return templates.TemplateResponse(
        "models.html",
        {"request": request, "config": config, "models_info": models_info},
    )


@app.get("/a-propos", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(
        "about.html",
        {"request": request, "config": config},
    )


@app.exception_handler(500)
async def http_exception_handler(request, exc):
    return FileResponse("templates/50x.html", status_code=500)


@app.exception_handler(StarletteHTTPException)
async def not_found_handler(request, exc):
    return templates.TemplateResponse(
        "404.html", {"request": request, "config": config}, status_code=404
    )


app = SentryAsgiMiddleware(app)
