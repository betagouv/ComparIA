from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List, Dict
from datetime import datetime
import logging
from fastapi.templating import Jinja2Templates

import time

from backend.models.data import models

templates = Jinja2Templates(directory="templates")

app = FastAPI()

# model_id, now, outage_details
models_errors: List = []

stream_logs = logging.StreamHandler()
stream_logs.setLevel(logging.INFO)  # You might want to add this handler to a logger

tests: List[Dict] = []  # Explicitly typing

scheduled_tasks = set()

import litellm

litellm._turn_on_debug()

from pydantic import BaseModel


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
def get_models() -> List[str]:  # Return type hint
    return models_errors


@app.get(
    "/",
    response_class=HTMLResponse,
)
def index(request: Request):
    # error_count = Dict()
    from languia.config import big_models, small_models, random_pool

    error_count = dict.fromkeys(models, 0)
    for model_id, _date, _details in models_errors:
        if model_id in error_count:
            error_count[model_id] += 1
    # print(str(error_count))
    return templates.TemplateResponse(
        "models_errors.html",
        {
            "models_errors": models_errors,
            "error_count": error_count,
            "models": models,
            "big_models": big_models,
            "small_models": small_models,
            "random_pool": random_pool,
            "request": request,
            "now": int(time.time()),
        },
    )
