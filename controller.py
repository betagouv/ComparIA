from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List, Dict
import asyncio
import time
from datetime import datetime
import logging
from fastapi.templating import Jinja2Templates
import traceback

import google.auth
import google.auth.transport.requests
import openai

import os
from typing import Dict
import json5

templates = Jinja2Templates(directory="templates")

app = FastAPI()
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# Outage is now a dictionary with time_of_outage and model_name
outages: List[Dict[str, str]] = []

stream_logs = logging.StreamHandler()
stream_logs.setLevel(logging.INFO)


@app.get("/outages/{model_name}/create", status_code=201)
@app.post("/outages/", status_code=201)
async def create_outage(model_name: str, reason: str = None, confirm: bool = True):
    outage = {
        "detection_time": datetime.now().isoformat(),
        "model_name": model_name,
        "reason": reason,
    }

    # Check if the model name already exists in the outages list
    existing_outage = next((o for o in outages if o["model_name"] == model_name), None)

    if existing_outage:
        await remove_outage(model_name)
    
    # Double-check the outage!!!
    if confirm:
        confirm_outage = await test_model(model_name)
        if confirm_outage["success"]:
            return "Didn't add to outages as test was successful"
    
    outages.append(outage)
    return outage

@app.get("/outages/")
async def get_outages():
    """
    Retrieves a list of all models currently off.

    Returns:
        List[str]: A list of model names.
    """
    return (o["model_name"] for o in outages)


@app.get("/outages/{model_name}/delete", status_code=204)
@app.delete("/outages/{model_name}", status_code=204)
async def remove_outage(model_name: str):
    """
    Removes an outage entry by model name.

    Args:
        model_name (str): The model name to remove from outages.

    Raises:
        HTTPException: If the model is not found in outages.
    """
    for i, outage in enumerate(outages):
        if outage["model_name"] == model_name:
            del outages[i]
            return {"success": True,
            "msg": f"{model_name} removed from outages"}
    raise HTTPException(status_code=404, detail="Model not found in outages")


if os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE"):
    register_api_endpoint_file = os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE")
else:
    register_api_endpoint_file = "register-api-endpoint-file.json"

models = json5.load(open(register_api_endpoint_file))


@app.get("/outages/{model_name}")
async def test_model(model_name):

    # Log the outage test
    logging.info(f"Testing model: {model_name} ")

    # Define test parameters
    test_message = "Say 'this is a test'."
    temperature = 1
    top_p = 1
    max_new_tokens = 10
    stream = False

    try:
        # Initialize the OpenAI client
        api_type = models[model_name]["api_type"]
        api_base = models[model_name]["api_base"]

        if api_type == "vertex":
            if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                logging.warn("No Google creds detected!")

            # Programmatically get an access token
            creds, project = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            # Note: the credential lives for 1 hour by default (https://cloud.google.com/docs/authentication/token-types#at-lifetime); after expiration, it must be refreshed.
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
            # Test without streaming
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
                await remove_outage(model_name)
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
            await create_outage(model_name, reason, confirm=False)
            return {"success": False, "error_message": reason}

    except Exception as e:
        reason = str(e)
        logging.error(f"Error: {reason}. Model: {model_name}")

        stacktrace = traceback.print_exc()
        _outage = await create_outage(model_name, reason, confirm=False)

        return {"success": False, "reason": str(reason), "stacktrace": stacktrace}


# async def scheduled_outage_tests():
#     while True:
#         # for model in models:
#         for outage in outages:
#             asyncio.create_task(test_model(outage["model_name"]))
#         await asyncio.sleep(600)  # Test every 10 minutes (600 seconds)


@app.get(
    "/",
    response_class=HTMLResponse,
)
async def index(request: Request):

    return templates.TemplateResponse(
        "outages.html",
        {"outages": outages, "models": models, "request": request},
    )
