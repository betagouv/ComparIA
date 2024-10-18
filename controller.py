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

# @app.post("/outages/", status_code=201)
@app.get("/outages/{model_name}/create", status_code=201)
def disable_model(model_name: str, reason: str = None):
    try:
        outage = {
            "detection_time": datetime.now().isoformat(),
            "model_name": model_name,
            "reason": reason,
        }

        # Check if the model name already exists in the outages list
        existing_outage = next((o for o in outages if o["model_name"] == model_name), None)

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
        raise


@app.get("/outages/")
def get_outages():
    """
    Retrieves a list of all models currently off.

    Returns:
        List[str]: A list of model names.
    """
    return (o["model_name"] for o in outages)


@app.get("/outages/{model_name}/delete", status_code=204)
@app.delete("/outages/{model_name}", status_code=204)
def remove_outages(model_name: str):
    """
    Removes an outage entry by model name.

    Args:
        model_name (str): The model name to remove from outages.

    Raises:
        HTTPException: If the model is not found in outages.
    """
    # try:
    for i, outage in enumerate(outages):
        if outage["model_name"] == model_name:
            del outages[i]
    # else:
    #     raise HTTPException(status_code=404, detail="Model not found in outages")
    return {"success": True,
            "msg": f"{model_name} removed from outages"}


if os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE"):
    register_api_endpoint_file = os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE")
else:
    register_api_endpoint_file = "register-api-endpoint-file.json"

models = json5.load(open(register_api_endpoint_file))


@app.get("/outages/{model_name}")
def test_model(model_name):
    global tests
    if model_name == "None":
        return {"success": False, "error_message": "Don't test 'None'!"}

    for test in tests:
        diff = int(time.time() - test["timestamp"])
        if test["model_name"] == model_name and (diff < 60*10):
            print(f"Already tested '{model_name}' {diff} seconds ago!")
            return {"success": False, "reason": f"Already tested '{model_name}' {diff} seconds ago!"}

    test = {"model_name": model_name, "timestamp": time.time()}
    tests.append(test)
    if len(tests) > 50:
        tests = tests[-50:]

    # Log the outage test
    logging.info(f"Testing model: {model_name} ")

    # Define test parameters
    test_message = "Say 'this is a test'."
    temperature = 1
    max_new_tokens = 10
    stream = False

    # Mark task as done
    if model_name in scheduled_tasks:
        scheduled_tasks.remove(model_name)

    try:
        # Initialize the OpenAI client
        api_type = models[model_name]["api_type"]
        api_base = models[model_name]["api_base"]

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
            api_key = models[model_name]["api_key"]
            
        client = openai.OpenAI(
            base_url=api_base,
            api_key=api_key,
            timeout=10,
        )
        # Send a test message to the OpenAI API
        res = client.chat.completions.create(
            model=models[model_name]["model_name"],
            messages=[{"role": "user", "content": test_message}],
            temperature=temperature,
            max_tokens=max_new_tokens,
            stream=stream,
        )

        # Verify the response
        text = ""
        if stream:
            for chunk in res:
                if chunk.choices:
                    text += chunk.choices[0].delta.content or ""
                    break
        else:
            if res.choices:
                text = res.choices[0].message.content or ""

        # Check if the response is successful
        if text:
            logging.info(f"Test successful: {model_name}")
            if any(outage["model_name"] == model_name for outage in outages):
                logging.info(f"Removing {model_name} from outage list")
                remove_outages(model_name)
                   
                return {
                    "success": True,
                    "message": "Removed model from outages list.",
                    "response": text,
                }
            return {"success": True, "message": "Model responded: " + str(text)}

        else:
            reason = f"No content from api for model {model_name}"
            logging.error(f"Test failed: {model_name}")
            logging.error(reason)
            disable_model(model_name, reason, confirm=False)
            return {"success": False, "error_message": reason}

    except Exception as e:
        reason = str(e)
        logging.error(f"Error: {reason}. Model: {model_name}")

        stacktrace = traceback.print_exc()
        _outage = disable_model(model_name, reason)

        return {"success": False, "reason": str(reason), "stacktrace": stacktrace}


@app.get(
    "/",
    response_class=HTMLResponse,
)
def index( request: Request, scheduled_tests: bool = False):
    return templates.TemplateResponse(
        "outages.html",
        {"outages": outages, "models": models, "request": request, "scheduled_tests": scheduled_tests},
    )


@app.get("/test_all_models")
def test_all_models(background_tasks: BackgroundTasks):
    """
    Initiates background tasks to test all models asynchronously.
    """
    for key, value in models.items():
        if key not in scheduled_tasks:
            try:
                background_tasks.add_task(test_model, key)
                scheduled_tasks.add(key)
            except Exception:
                pass
    return RedirectResponse(url="/?scheduled_tests=true", status_code=302)



# async def periodic_test_all_models():
#     """
#     Periodically test a model in the background.
#     """
#     while True:
#         logging.info("Periodic testing models")
#         test_all_models()
#         await asyncio.sleep(3600)  # Test every hour


# @app.on_event("startup")
# async def start_periodic_tasks():
#     # Schedule the periodic model testing task
#     asyncio.create_task(periodic_test_all_models())