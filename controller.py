import logging
import time
from datetime import datetime
from typing import Any, Dict, List

import litellm
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from backend.language_models.data import get_models

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
    models = get_models()

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
            "models": models.enabled,
            "big_models": models.big_models,
            "small_models": models.small_models,
            "random_pool": models.random_models,
            "request": request,
            "now": int(time.time()),
        },
    )
