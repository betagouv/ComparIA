from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from starlette.exceptions import HTTPException as StarletteHTTPException

from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from languia.block_arena import demo

import logging
import gradio as gr

from languia import config

from languia.utils import size_desc, license_desc, license_attrs, test_all_models

app = FastAPI()

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
# app.mount("/arene/custom_components", StaticFiles(directory="custom_components"), name="custom_components")

templates = Jinja2Templates(directory="templates")

# TODO: use gr.set_static_paths(paths=["test/test_files/"])?
gr.set_static_paths(paths=[config.assets_absolute_path])
# broken... using path set up by fastapi instead 
logging.info("Allowing assets absolute path: " + config.assets_absolute_path)

# Set authorization credentials
auth = None

# Clashes with hot reloading
if not config.debug:
    test_all_models(config.controller_url)

# TODO: Fine-tune for performance https://www.gradio.app/guides/setting-up-a-demo-for-maximum-performance
demo = demo.queue(
    default_concurrency_limit=None,
    # default_concurrency_limit=40,
    # status_update_rate="auto",
    api_open=False,
)

app = gr.mount_gradio_app(
    app,
    demo,
    path="/arene",
    root_path="/arene",
    # allowed_paths=[config.assets_absolute_path],
    allowed_paths=[
        config.assets_absolute_path,
        "/tmp",
        "/tmp/gradio",
        "custom_components",
    ],
    show_error=config.debug,
)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request, "config": config}
    )


@app.get("/modeles", response_class=HTMLResponse)
async def models(request: Request):
    return templates.TemplateResponse(
        "models.html",
        {
            "request": request,
            "config": config,
            "models": config.models_extra_info,
            "size_desc": size_desc,
            "license_desc": license_desc,
            "license_attrs": license_attrs,
        },
    )


@app.get("/a-propos", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse(
        "about.html",
        {"request": request, "config": config},
    )


@app.get("/partenaires", response_class=HTMLResponse)
async def partners(request: Request):
    return templates.TemplateResponse(
        "partners.html",
        {"request": request, "config": config},
    )


@app.get("/mentions-legales", response_class=HTMLResponse)
async def legal(request: Request):
    return templates.TemplateResponse(
        "legal.html",
        {"request": request, "config": config},
    )


@app.get("/donnees-personnelles", response_class=HTMLResponse)
async def policy(request: Request):
    return templates.TemplateResponse(
        "policy.html",
        {"request": request, "config": config},
    )


@app.get("/modalites", response_class=HTMLResponse)
async def tos(request: Request):
    return templates.TemplateResponse(
        "tos.html",
        {"request": request, "config": config, "models": config.models_extra_info},
    )


@app.get("/accessibilite", response_class=HTMLResponse)
async def accessibility(request: Request):
    return templates.TemplateResponse(
        "accessibility.html",
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
