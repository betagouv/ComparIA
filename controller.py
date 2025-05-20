from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List, Dict
from datetime import datetime
import logging
from fastapi.templating import Jinja2Templates
import traceback


from languia.utils import EmptyResponseError, ContextTooLongError

from languia.litellm import litellm_stream_iter

import time

import os

# from typing import Dict
import json5

templates = Jinja2Templates(directory="templates")

app = FastAPI()
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

unavailable_models = {}

always_available_models = set(["o3-mini", "o4-mini", "grok-3-mini-beta", "qwen3-32b"])


stream_logs = logging.StreamHandler()
stream_logs.setLevel(logging.INFO)

tests: List = []

scheduled_tasks = set()

import litellm

litellm._turn_on_debug()

@app.get("/always_available_models/{model_id}/create", status_code=201)
@app.post("/always_available_models/{model_id}/create", status_code=201)
def create_always_available_models(model_id: str, test: dict = None):
    global always_available_models
    if model_id not in always_available_models:
        print("always_available_models " + model_id)
        always_available_models.add("model_id")
    else:
        return False

@app.get("/unavailable_models/{model_id}/create", status_code=201)
@app.post("/unavailable_models/{model_id}/create", status_code=201)
def disable_model(model_id: str, test: dict = None):
    global unavailable_models
    if model_id not in always_available_models:
        print("disabling " + model_id)
        outage = {
            "detection_time": datetime.now().isoformat(),
            "model_id": model_id,
        }
        if test:
            outage.update(test)
        unavailable_models[outage["model_id"]] = outage

        return outage
    else:
        return False


@app.get("/unavailable_models/")
def get_unavailable_models():
    return (model_id for model_id, _outage in unavailable_models.items())


@app.get("/unavailable_models/{model_id}/delete", status_code=204)
@app.delete("/unavailable_models/{model_id}", status_code=204)
def remove_unavailable_models(model_id: str):
    if model_id in unavailable_models:
        del unavailable_models[model_id]
        return True
    else:
        return False


@app.get("/always_available_models/{model_id}/delete", status_code=204)
@app.delete("/always_available_models/{model_id}", status_code=204)
def remove_always_available_models(model_id: str):
    if model_id in always_available_models:
        always_available_models.remove(model_id)
        return True
    else:
        return False


if os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE"):
    register_api_endpoint_file = os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE")
else:
    register_api_endpoint_file = "register-api-endpoint-file.json"

endpoints = json5.load(open(register_api_endpoint_file))


@app.get("/unavailable_models/{model_id}")
def test_model(model_id):
    global tests
    if model_id == "None":
        return {"success": False, "error_message": "Don't test 'None'!"}

    from languia.utils import get_endpoint

    endpoint = get_endpoint(model_id)

    # Log the outage test
    logging.info(f"Testing endpoint: {model_id}")

    # Define test parameters
    temperature = 1
    max_new_tokens = 100
    # stream = True

    try:
        endpoint = get_endpoint(model_id)

        model_name = endpoint.get("api_type", "openai") + "/" + endpoint["model_name"]

        # stream=model_api_dict.get("stream", True),
        # top_p=top_p,
        include_reasoning = False
        enable_reasoning = False
        
        recommended_config = endpoint.get("recommended_config", None)
        if recommended_config is not None:
            include_reasoning = recommended_config.get("include_reasoning", False)
            enable_reasoning = recommended_config.get("enable_reasoning", False)

        stream_iter = litellm_stream_iter(
            model_name=model_name,
            messages=[{"role": "user", "content": "ONLY say 'this is a test'."}],
            api_key=endpoint.get("api_key", "F4K3-4P1-K3Y"),
            api_base=endpoint.get("api_base", None),
            api_version=endpoint.get("api_version", None),
            temperature=temperature,
            max_new_tokens=max_new_tokens,
            vertex_ai_location=endpoint.get("vertex_ai_location", None),
            include_reasoning=include_reasoning,
            enable_reasoning=enable_reasoning,
        )

        # Verify the response
        text = ""
        output_tokens = None
        for data in stream_iter:
            if "output_tokens" in data:
                print(
                    f"reported output tokens for api {endpoint['api_id']}:"
                    + str(data["output_tokens"])
                )
                output_tokens = data["output_tokens"]

            output = data.get("text", data.get("reasoning"))
            if output:
                text = output

        test = {
            "model_id": model_id,
            "timestamp": int(time.time()),
        }
        if output_tokens:
            test.update(output_tokens=output_tokens)


        # FIXME: Add ugly bypass for reasoning models...
        if (
            text
            or include_reasoning
            or model_id in always_available_models):
            logging.info(f"Test successful: {model_id}")
            if remove_unavailable_models(model_id):
                test.update({"info": "Removed model from unavailable_models list."})

            test.update(
                {
                    "success": True,
                    "message": "Model responded: " + str(text),
                }
            )
            if model_id in always_available_models:

                test.update(
                    {
                        "success": True,
                        "message": "Model in list of always_available_models",
                    }
                )
        else:
            reason = f"No content from model {model_id}"
            # logging.error(f"Test failed: {model_name}")
            # logging.error(reason)
            # test.update({"success": False, "message": reason})
            raise (EmptyResponseError(reason))
        tests.append(test)
        if len(tests) > 25:
            tests = tests[-25:]
            # disable_endpoint(model_name, reason)
        return test
    except Exception as e:
        if e == ContextTooLongError:

            test = {
                "model_id": model_id,
                "timestamp": int(time.time()),
            }
            logging.info(f"Test successful: {model_id}")
            if remove_unavailable_models(model_id):
                test.update({"info": "Removed model from unavailable_models list."})

            test.update(
                {
                    "success": True,
                    "message": "Model responded: " + str(text),
                }
            )
            return test

        reason = str(e)
        logging.error(f"Error: {reason}. Model: {model_id}")
        stacktrace = traceback.print_exc()
        test = {
            "model_id": model_id,
            "timestamp": int(time.time()),
            "success": False,
            "message": reason,
            "stacktrace": stacktrace,
        }

        disable_model(model_id, test)
        tests.append(test)
        if len(tests) > 25:
            tests = tests[-25:]
        return test


@app.get(
    "/",
    response_class=HTMLResponse,
)
def index(request: Request, scheduled_tests: bool = False):
    global tests
    return templates.TemplateResponse(
        "unavailable_models.html",
        {
            "tests": tests,
            "unavailable_models": unavailable_models,
            "always_available_models":always_available_models,
            "endpoints": endpoints,
            "request": request,
            "scheduled_tests": scheduled_tests,
            "now": int(time.time()),
        },
    )


@app.get("/test_all_endpoints")
def test_all_endpoints(background_tasks: BackgroundTasks):
    """
    Initiates background tasks to test all models asynchronously.
    """
    for endpoint in endpoints:
        if endpoint.get("model_id") not in always_available_models:
            try:
                background_tasks.add_task(test_model, endpoint.get("model_id"))
            except Exception:
                pass
    return RedirectResponse(url="/?scheduled_tests=true", status_code=302)


# async def periodic_test_all_endpoints():
#     """
#     Periodically test a model in the background.
#     """
#     while True:
#         logging.info("Periodic testing models")
#         test_all_endpoints()
#         await asyncio.sleep(3600)  # Test every hour


# @app.on_event("startup")
# async def start_periodic_tasks():
#     # Schedule the periodic model testing task
#     asyncio.create_task(periodic_test_all_endpoints())