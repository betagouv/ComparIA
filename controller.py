from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List, Dict
from datetime import datetime
import logging
from fastapi.templating import Jinja2Templates
import traceback

from languia.api_provider import openai_stream

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

    import openai, os

    if os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE"):
        register_api_endpoint_file = os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE")
    else:
        register_api_endpoint_file = "register-api-endpoint-file.json"

    # from languia.utils import get_endpoint
    # endpoint = get_endpoint(api_id)
    
    from languia.config import api_endpoint_info
    # import json5  
    # api_endpoint_info = json5.load(open(register_api_endpoint_file))

    for endpoint in api_endpoint_info:
        print(endpoint)
        if endpoint.get("api_id") == api_id:
            break
        endpoint = None
    # api_key = os.getenv("OPENROUTER_API_KEY")
    # api_base = "https://openrouter.ai/api/v1/"
    # model_name = "nousresearch/hermes-3-llama-3.1-405b:free"

    api_base = endpoint["api_base"]
    api_key = endpoint["api_key"]
    model_name = endpoint["model_name"]

    print (api_base)
    print (api_key)
    print (model_name)

    messages_dict = [{"role": "user", "content": "Say hello!"}]

    client = openai.OpenAI(
        base_url=api_base,
        api_key=api_key,
        # max_retries=
        #         timeout=WORKER_API_TIMEOUT,
        # timeout=5,
        #     timeout=httpx.Timeout(5, read=5, write=5, connect=2
        # )
    )

    response = client.chat.completions.create(
        model=model_name,
        messages=messages_dict,
        temperature=1,
        max_tokens=100,
        stream=True,
        stream_options={"include_usage": True},
        # Not available like this
        # top_p=top_p,
    )
    # Verify the response
    text = ""
    output_tokens = None
    for chunk in response:
        if "output_tokens" in chunk:
            print(f"reported output tokens for api test:" + str(chunk["output_tokens"]))
            output_tokens = chunk["output_tokens"]

        if len(chunk.choices) > 0:
            text += chunk.choices[0].delta.content or ""

    if output_tokens:
        print(output_tokens)

    # Check if the response is successful
    if text:
        print(text)
    else:
        print("Argh!")
    return text


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
