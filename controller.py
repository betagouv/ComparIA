from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from typing import List, Dict
import asyncio
import time
from datetime import datetime
import logging
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")

app = FastAPI()

# Outage is now a dictionary with time_of_outage and model_name
outages: List[Dict[str, str]] = []

stream_logs = logging.StreamHandler()
stream_logs.setLevel(logging.INFO)

@app.post("/outages/", status_code=201)
async def create_outage(model_name: str, reason:str=None):
    outage = {
        "detection_time": datetime.now().isoformat(),
        "model_name": model_name,
        "reason": reason
    }

    # Check if the model name already exists in the outages list
    existing_outage = next((o for o in outages if o["model_name"] == model_name), None)

    if existing_outage:
        outages[model_name]["detection_time"] = outage["detection_time"]
        if hasattr(outage,"reason"):
            outages[model_name]["reason"] = outage["reason"]
    else:
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
            return
    raise HTTPException(status_code=404, detail="Model not found in outages")


import os
import openai
from typing import Dict
import json

if os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE"):
    register_api_endpoint_file = os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE")
else:
    register_api_endpoint_file = "register-api-endpoint-file.json"

models = json.load(open(register_api_endpoint_file))

@app.get("/outages/{model_name}")
async def test_model(model_name):

    # Log the outage test
    logging.info(
        f"Testing model: {model_name} "
    )

    # Define test parameters
    test_message = "Say 'this is a test'."
    temperature = 1
    top_p = 1
    max_new_tokens = 10


# if api_endpoint_info[model_name]["api_type"] == "openai"

    try:
        # Initialize the OpenAI client
        api_key = models[model_name]["api_key"]
        api_base = models[model_name]["api_base"]
        client = openai.OpenAI(
            base_url=api_base,
            api_key=api_key,
            timeout=180,
        )
        # Send a test message to the OpenAI API
        res = client.chat.completions.create(
            model=models[model_name]["model_name"],
            messages=[{"role": "user", "content": test_message}],
            temperature=temperature,
            max_tokens=max_new_tokens,
            stream=True,
        )

        # Verify the response
        text = ""
        for chunk in res:
            if len(chunk.choices) > 0:
                text += chunk.choices[0].delta.content or ""
                break

        # Check if the response is successful
        if text:
            logging.info(f"Test successful: {model_name}")
            if any(outage["model_name"] == model_name for outage in outages):
                logging.info(f"Removing {model_name} from outage list")
                await remove_outage(model_name)
                return {"success": "true", "message": "Removed model from outages list.", "response": text}
            return {"success": "true", "message": "Model responded: "+str(text)}

        else:
            reason = "No content in: "+str(chunk)
            logging.error(f"Test failed: {model_name}")
            logging.error(f"No text in: {chunk}")
            await create_outage(model_name, reason)
            return {"success": "false", "error_message": reason}

    except Exception as e:
        logging.error(f"Error: {model_name}, {str(e)}")
        
        outage = await create_outage(model_name, e)

        return {"success": "false", "reason": str(e)}


async def scheduled_outage_tests():
    while True:
        # for model in models:
        for outage in outages:
            asyncio.create_task(test_model(outage['model_name']))
        await asyncio.sleep(600)  # Test every 10 minutes (600 seconds)


@app.get("/", response_class=HTMLResponse, )
async def index(request: Request):
    
    return templates.TemplateResponse(
        "outages.html",
        {"outages": outages, "models": models, "request": request},
    )