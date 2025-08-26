from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List, Dict, Union  # Added Union for return types
from datetime import datetime
import logging
from fastapi.templating import Jinja2Templates

import time

import os

# from typing import Dict # Already imported Dict from typing
import json5

templates = Jinja2Templates(directory="templates")

app = FastAPI()
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

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


if os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE"):
    register_api_endpoint_file = os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE")
else:
    register_api_endpoint_file = "register-api-endpoint-file.json"

# Ensure the file exists before trying to load, or handle FileNotFoundError
try:
    with open(register_api_endpoint_file, "r") as f:
        endpoints = json5.load(f)
except FileNotFoundError:
    logging.error(
        f"Endpoint configuration file not found: {register_api_endpoint_file}"
    )
    endpoints = []  # Default to empty list if file not found
except Exception as e:
    logging.error(f"Error loading endpoint configuration file: {e}")
    endpoints = []


@app.get(
    "/",
    response_class=HTMLResponse,
)
def index(request: Request):
    # error_count = Dict()
    error_count = dict.fromkeys([endpoint["model_id"] for endpoint in endpoints], 0)
    for model_id, _date, _details in models_errors:
        if model_id in error_count:
            error_count[model_id] += 1

    return templates.TemplateResponse(
        "models_errors.html",
        {
            "models_errors": models_errors,
            "error_count": error_count,
            "endpoints": endpoints,
            "request": request,
            "now": int(time.time()),
        },
    )
