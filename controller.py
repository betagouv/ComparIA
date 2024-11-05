from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List, Dict
from datetime import datetime
import logging
from fastapi.templating import Jinja2Templates
import traceback

# import sentry_sdk
# from fastapi import BackgroundTasks

# from sentry_sdk.integrations.fastapi import FastApiIntegration

import google.auth
import google.auth.transport.requests
import openai

import time

import os

# from typing import Dict
import json5

# if os.getenv("SENTRY_DSN"):
#     sentry_sdk.init(
#     dsn=os.getenv("SENTRY_DSN"),
#     # integrations=[FastApiIntegration()], + Starlette
#     traces_sample_rate=1.0,
#     profiles_sample_rate=1.0,
# )

templates = Jinja2Templates(directory="templates")

app = FastAPI()
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

outages: List[Dict[str, str]] = []

stream_logs = logging.StreamHandler()
stream_logs.setLevel(logging.INFO)

tests: List = []

scheduled_tasks = set()


@app.get("/outages/{model_name}/delete", status_code=204)
@app.delete("/outages/{model_name}", status_code=204)
def remove_outages(api_id: str):
    # try:
    for i, outage in enumerate(outages):
        if outage["api_id"] == api_id:
            del outages[i]
    # else:
    #     raise HTTPException(status_code=404, detail="Model not found in outages")
    return {"success": True, "msg": f"{api_id} removed from outages"}


# @app.post("/outages/", status_code=201)
@app.get("/outages/{api_id}/create", status_code=201)
def disable_endpoint(api_id: str, reason: str = None):
    try:
        outage = {
            "detection_time": datetime.now().isoformat(),
            "api_id": api_id,
            "model_id": api_id,
            "reason": reason,
        }

        # Check if the api_id already exists in the outages list
        existing_outage = next((o for o in outages if o["api_id"] == api_id), None)

        if existing_outage:
            # remove_outages(model_name)
            return existing_outage

        # Double-check the outage!!!
        # if confirm:
        #     confirm_outage = test_model(model_name)
        #     if confirm_outage["success"]:
        #         return "Didn't add to outages as test was successful"

        outages.append(outage)

        # Schedule background task to test the model periodically
        # if background_tasks:
        #     background_tasks.add_task(periodic_test_model, model_name)

        return outage

    # except HTTPException as e:
    #     if e.status_code == 422:
    #         print("Couldn't get the whole reason: ")
    #         print(reason)
    #         outage = {
    #             "detection_time": datetime.now().isoformat(),
    #             "model_name": model_name,
    #             "reason": "Too long to be posted",
    #         }
    #         outages.append(outage)
    #     else:
    #         raise
    except Exception as _e:
        # if os.getenv("SENTRY_DSN"):
        #     sentry_sdk.capture_exception(e)

        outages.append(outage)

        if existing_outage:
            remove_outages(api_id)
        # Check if the model name already exists in the outages list
        existing_outage = next((o for o in outages if o["api_id"] == api_id), None)

        return outage


@app.get("/outages/")
def get_outages():
    """
    Retrieves a list of all models currently off.

    Returns:
        List[str]: A list of model names.
    """
    return ({o["model_name"], o["endpoint_name"]} for o in outages)


if os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE"):
    register_api_endpoint_file = os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE")
else:
    register_api_endpoint_file = "register-api-endpoint-file.json"

endpoints = json5.load(open(register_api_endpoint_file))


@app.get("/outages/{api_id}")
def test_model(api_id):
    global tests
    if api_id == "None":
        return {"success": False, "error_message": "Don't test 'None'!"}

    # for test in tests:
    #     diff = int(time.time() - test["timestamp"])
    #     if test["model_name"] == model_name and (diff < 60 * 5):
    #         if diff < 60:
    #             time_ago = f"{diff}s"
    #         else:
    #             minutes = diff // 60
    #             seconds = diff % 60
    #             time_ago = f"{minutes}min {seconds}s"
    #         print(f"Already tested '{model_name}' {time_ago} ago!")
    #         return {
    #             "success": False,
    #             "reason": f"Already tested '{model_name}' {time_ago} ago!",
    #         }
    from languia.utils import get_endpoint

    endpoint = get_endpoint(api_id)

    # Log the outage test
    logging.info(f"Testing endpoint: {api_id} ")

    # Define test parameters
    test_message = "Say 'this is a test'."
    temperature = 1
    max_new_tokens = 10
    stream = True

    # Mark task as done
    # if model_name in scheduled_tasks:
    #     scheduled_tasks.remove(model_name)

    try:
        endpoint = get_endpoint(api_id)
        # Initialize the OpenAI client
        api_type = endpoint.get("api_type")
        api_base = endpoint.get("api_base")

        if api_type == "vertex":
            if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                logging.warn("No Google creds detected!")

            creds, project = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            api_key = creds.token
        else:
            api_key = endpoint.get("api_key")

        client = openai.OpenAI(
            base_url=api_base,
            api_key=api_key,
            timeout=10,
        )
        # Send a test message to the OpenAI API
        res = client.chat.completions.create(
            model=endpoint.get("model_name"),
            messages=[{"role": "user", "content": test_message}],
            temperature=temperature,
            max_tokens=max_new_tokens,
            stream=stream,
            stream_options={"include_usage": True},
        )

        # Verify the response
        text = ""
        if stream:
            for chunk in res:
                if chunk.choices:
                    text += chunk.choices[0].delta.content or ""
        else:
            if res.choices:
                text = res.choices[0].message.content or ""

        test = {
            "model_id": endpoint.get("model_id"),
            "api_id": api_id,
            "timestamp": int(time.time()),
        }

        # Check if the response is successful
        if text:
            logging.info(f"Test successful: {api_id}")
            if any(outage["api_id"] == api_id for outage in outages):
                logging.info(f"Removing {api_id} from outage list")
                remove_outages(api_id)

            test.update(
                {
                    "success": True,
                    "info": "Removed model from outages list.",
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
        _outage = disable_endpoint(api_id, reason)

        return {"success": False, "message": str(reason), "stacktrace": stacktrace}


@app.get(
    "/",
    response_class=HTMLResponse,
)
def index(request: Request, scheduled_tests: bool = False):
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
                background_tasks.add_task(test_model, endpoint.get("api_id"))
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
