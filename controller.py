from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List, Dict
from datetime import datetime
import logging
from fastapi.templating import Jinja2Templates
import traceback

from languia.api_provider import get_api_provider_stream_iter

from gradio import ChatMessage

import time

import os

# from typing import Dict
import json5

templates = Jinja2Templates(directory="templates")

app = FastAPI()
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

outages = {}

stream_logs = logging.StreamHandler()
stream_logs.setLevel(logging.INFO)

tests: List = []

scheduled_tasks = set()


@app.post("/outages/{api_id}/create", status_code=201)
def disable_endpoint(api_id: str, test: dict = None):
    global outages
    print("disabling " + api_id)
    outage = {
        "detection_time": datetime.now().isoformat(),
        "api_id": api_id,
        # "model_id": api_id,
    }
    outage.update(test)
    outages[outage["api_id"]] = outage

    return outage


@app.get("/outages/")
def get_outages():
    return (api_id for api_id, _outage in outages.items())


@app.get("/outages/{api_id}/delete", status_code=204)
@app.delete("/outages/{api_id}", status_code=204)
def remove_outages(api_id: str):
    if api_id in outages:
        del outages[api_id]
        return True
    else:
        return False


if os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE"):
    register_api_endpoint_file = os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE")
else:
    register_api_endpoint_file = "register-api-endpoint-file.json"

endpoints = json5.load(open(register_api_endpoint_file))


@app.get("/outages/{api_id}")
def test_endpoint(api_id):
    global tests
    if api_id == "None":
        return {"success": False, "error_message": "Don't test 'None'!"}

    from languia.utils import get_endpoint

    endpoint = get_endpoint(api_id)

    # Log the outage test
    logging.info(f"Testing endpoint: {api_id}")

    # Define test parameters
    temperature = 1
    max_new_tokens = 10
    stream = True

    try:
        endpoint = get_endpoint(api_id)

        stream_iter = get_api_provider_stream_iter(
            [ChatMessage(role="user", content="ONLY say 'this is a test'.")],
            endpoint,
            temperature,
            max_new_tokens,
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

            output = data.get("text")
            if output:
                output.strip()
                text += output

        test = {
            "model_id": endpoint.get("model_id"),
            "api_id": api_id,
            "timestamp": int(time.time()),
        }
        if output_tokens:
            test.update(output_tokens=output_tokens)

        # Check if the response is successful
        if text:
            logging.info(f"Test successful: {api_id}")
            if remove_outages(api_id):
                test.update({"info": "Removed model from outages list."})

            test.update(
                {
                    "success": True,
                    "message": "Model responded: " + str(text),
                }
            )
        else:
            reason = f"No content from api {api_id}"
            # logging.error(f"Test failed: {model_name}")
            logging.error(reason)
            test.update({"success": False, "message": reason})
        tests.append(test)
        if len(tests) > 25:
            tests = tests[-25:]
            # disable_endpoint(model_name, reason)
        return test
    except Exception as e:
        reason = str(e)
        logging.error(f"Error: {reason}. Endpoint: {api_id}")
        stacktrace = traceback.print_exc()
        test = {
            "model_id": endpoint.get("model_id"),
            "api_id": api_id,
            "timestamp": int(time.time()),
            "success": False,
            "message": reason,
            "stacktrace": stacktrace,
        }

        disable_endpoint(api_id, test)
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
        "outages.html",
        {
            "tests": tests,
            "outages": outages,
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
        if endpoint.get("api_id") not in scheduled_tasks:
            try:
                background_tasks.add_task(test_endpoint, endpoint.get("api_id"))
                scheduled_tasks.add(endpoint.get("api_id"))
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
