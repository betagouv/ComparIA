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

from languia.reveal import size_desc, license_desc, license_attrs

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
# if not config.debug:
#     test_all_endpoints(config.controller_url)

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

from languia.utils import get_gauge_count

objective = 50000


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    gauge_count = get_gauge_count()
    gauge_count_ratio = str(int(100 * get_gauge_count() / objective))
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "config": config,
            "gauge_count_ratio": gauge_count_ratio,
            "gauge_count": gauge_count,
            "objective": objective,
        },
    )


@app.get("/modeles", response_class=HTMLResponse)
async def models(request: Request):
    return templates.TemplateResponse(
        "models.html",
        {
            "title": "Liste des modèles",
            "request": request,
            "config": config,
            "models": config.models_extra_info,
            "size_desc": size_desc,
            "license_desc": license_desc,
            "license_attrs": license_attrs,
        },
    )


@app.get("/share", response_class=HTMLResponse)
async def share(i: str, request: Request):

    from languia.config import all_models_extra_info_toml
    try:
        import base64, json
        decoded = base64.b64decode(i)
        print(decoded)
        data = json.loads(decoded)
        print(data)
        print(all_models_extra_info_toml)
        assert data.get("a") in all_models_extra_info_toml
        model_a_name = data.get("a")
        print(model_a_name)
        assert data.get("b") in all_models_extra_info_toml
        model_b_name = data.get("b")
        print(model_b_name)
        assert isinstance(data.get("ta"), int)
        model_a_tokens = data.get("ta")
        assert isinstance(data.get("tb"), int)
        model_b_tokens = data.get("tb")
        assert (data.get("c") in ['a','b'] or data.get("c") == None)
        if data.get("c") == "a":
            chosen_model = "model-a"
        elif data.get("c") == "b":
            chosen_model = "model-b"
        else:
            chosen_model = None
    except:
        return FileResponse("templates/50x.html", status_code=500)

    from languia.utils import get_model_extra_info
    from languia.config import models_extra_info

    model_a = get_model_extra_info(model_a_name, models_extra_info)
    model_b = get_model_extra_info(model_b_name, models_extra_info)

    from languia.reveal import (
        get_llm_impact,
        calculate_lightbulb_consumption,
        calculate_streaming_hours,
    )

    model_a_impact = get_llm_impact(model_a, model_a_name, model_a_tokens, None)
    model_b_impact = get_llm_impact(model_b, model_b_name, model_b_tokens, None)

    lightbulb_a, lightbulb_a_unit = calculate_lightbulb_consumption(
        model_a_impact.energy.value
    )
    lightbulb_b, lightbulb_b_unit = calculate_lightbulb_consumption(
        model_b_impact.energy.value
    )

    streaming_a, streaming_a_unit = calculate_streaming_hours(model_a_impact.gwp.value)
    streaming_b, streaming_b_unit = calculate_streaming_hours(model_b_impact.gwp.value)

    return templates.TemplateResponse(
        "share.html",
        {
            "b64": i,
            "title": "Mon bilan",
            "model_a": model_a,
            "model_b": model_b,
            "chosen_model": chosen_model,
            "model_a_impact": model_a_impact,
            "model_b_impact": model_b_impact,
            "size_desc": size_desc,
            "license_desc": license_desc,
            "license_attrs": license_attrs,
            "model_a_tokens": model_a_tokens,
            "model_b_tokens": model_b_tokens,
            "streaming_a": streaming_a,
            "streaming_a_unit": streaming_a_unit,
            "streaming_b": streaming_b,
            "streaming_b_unit": streaming_b_unit,
            "lightbulb_a": lightbulb_a,
            "lightbulb_a_unit": lightbulb_a_unit,
            "lightbulb_b": lightbulb_b,
            "lightbulb_b_unit": lightbulb_b_unit,
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
        {
            "title": "À propos",
            "request": request,
            "config": config,
        },
    )


@app.get("/faq", response_class=HTMLResponse)
async def faq(request: Request):
    return templates.TemplateResponse(
        "faq.html",
        {
            "title": "Vos questions les plus courantes",
            "request": request,
            "config": config,
        },
    )


@app.get("/partenaires", response_class=HTMLResponse)
async def partners(request: Request):
    return templates.TemplateResponse(
        "partners.html",
        {
            "title": "Partenaires",
            "request": request,
            "config": config,
        },
    )


@app.get("/mentions-legales", response_class=HTMLResponse)
async def legal(request: Request):
    return templates.TemplateResponse(
        "legal.html",
        {
            "title": "Mentions légales",
            "request": request,
            "config": config,
        },
    )


@app.get("/donnees-personnelles", response_class=HTMLResponse)
async def policy(request: Request):
    return templates.TemplateResponse(
        "policy.html",
        {
            "title": "Politique de confidentialité",
            "request": request,
            "config": config,
        },
    )


@app.get("/modalites", response_class=HTMLResponse)
async def tos(request: Request):
    return templates.TemplateResponse(
        "tos.html",
        {
            "title": "Modalités d’utilisation",
            "request": request,
            "config": config,
            "models": config.models_extra_info,
        },
    )


@app.get("/accessibilite", response_class=HTMLResponse)
async def accessibility(request: Request):
    return templates.TemplateResponse(
        "accessibility.html",
        {
            "title": "Déclaration d’accessibilité",
            "request": request,
            "config": config,
        },
    )


@app.get("/bnf", response_class=HTMLResponse)
async def bnf(request: Request):
    return templates.TemplateResponse(
        "bnf.html",
        {
            "title": "Evénement 7 février",
            "request": request,
            "config": config,
        },
    )


@app.exception_handler(500)
async def http_exception_handler(request, exc):
    return FileResponse("templates/50x.html", status_code=500)


@app.exception_handler(StarletteHTTPException)
async def not_found_handler(request, exc):
    return templates.TemplateResponse(
        "404.html",
        {"title": "Page non trouvée", "request": request, "config": config},
        status_code=404,
    )


app = SentryAsgiMiddleware(app)
