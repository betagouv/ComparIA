import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from languia.gradio_web_server import demo
# TODO: don't use?
from fastchat.utils import build_logger
import gradio as gr

app = FastAPI()
# os.makedirs("static", exist_ok=True)
# app.mount("/static", StaticFiles(directory="static"), name="static")
# templates = Jinja2Templates(directory="templates")


# @app.get("/", response_class=HTMLResponse)
# async def home(request: Request):
#     return templates.TemplateResponse(
#         "models.html", {"request": request, "videos": videos})

# @app.get("/arena/")
# async def serve_arena(request: Request):
#     return RedirectResponse(url='/', status_code=200)

logger = build_logger("languia", "languia.log")

env_debug = os.getenv("LANGUIA_DEBUG")

if env_debug:
    if env_debug.lower() == "true":
        debug = True

if not debug:
    assets_absolute_path = "/app/assets"
else:
    assets_absolute_path = (
        os.path.dirname(__file__)
        + "/assets"
    )
app = gr.mount_gradio_app(
    app,
    demo,
    path="/arena",
    root_path="/arena",
    allowed_paths=[
        assets_absolute_path
    ],
)

# Set authorization credentials
auth = None

# TODO: Re-enable / Fine-tune for performance https://www.gradio.app/guides/setting-up-a-demo-for-maximum-performance
# demo = demo.queue(
#     default_concurrency_limit=args.concurrency_count,
#     status_update_rate=10,

#     api_open=False,
# )

if os.getenv("SENTRY_DSN"):
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    if os.getenv("SENTRY_SAMPLE_RATE"):
        traces_sample_rate = float(os.getenv("SENTRY_SAMPLE_RATE"))
    else:
        traces_sample_rate = 0.2
    logger.info("Sentry loaded with traces_sample_rate=" + str(traces_sample_rate))
    if os.getenv("SENTRY_ENV"):
        sentry_env = os.getenv("SENTRY_ENV")
    else:
        sentry_env = "development"
        sentry_sdk.init(
            dsn=os.getenv("SENTRY_DSN"),
            environment=sentry_env,
            traces_sample_rate=traces_sample_rate,
        )
# TODO: use gr.set_static_paths(paths=["test/test_files/"])?
# Note: access via e.g. DOMAIN/file=assets/fonts/Marianne-Bold.woff
logger.info("Allowing assets absolute path: " + assets_absolute_path)
app = SentryAsgiMiddleware(app)