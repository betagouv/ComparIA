import logging
import time
from datetime import datetime

import litellm
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from backend.config import DEFAULT_COUNTRY_PORTAL
from backend.llms.data import get_llms_data

templates = Jinja2Templates(directory="templates")

app = FastAPI()

# model_id, now, outage_details
models_errors: list = []

stream_logs = logging.StreamHandler()
stream_logs.setLevel(logging.INFO)  # You might want to add this handler to a logger

# FIXME not used?
# tests: list[dict] = []  # Explicitly typing
# scheduled_tasks = set()


litellm._turn_on_debug()


class ErrorData(BaseModel):
    error: str


@app.get("/models/{model_id}/error", status_code=201)
@app.post("/models/{model_id}/error", status_code=201)
def report_model(model_id: str, error: ErrorData | None = None) -> bool:

    global models_errors
    if error and error.error:
        msg = error.error
    else:
        msg = None
    models_errors.append([model_id, datetime.now(), msg])
    return True


@app.get("/errors")
def get_models_errors() -> list[str]:  # Return type hint
    return models_errors


@app.get(
    "/",
    response_class=HTMLResponse,
)
def index(request: Request) -> HTMLResponse:
    models = get_llms_data(DEFAULT_COUNTRY_PORTAL)

    error_count = dict.fromkeys(models.enabled, 0)
    for model_id, _date, _details in models_errors:
        if model_id in error_count:
            error_count[model_id] += 1
    # print(str(error_count))
    return templates.TemplateResponse(
        "models_errors.html",
        {
            "models_errors": models_errors,
            "error_count": error_count,
            "models": {k: v.model_dump() for k, v in models.enabled.items()},
            "big_models": models.big_models,
            "small_models": models.small_models,
            "random_pool": models.random_models,
            "request": request,
            "now": int(time.time()),
        },
    )
