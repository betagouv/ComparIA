from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List, Dict, Union  # Added Union for return types
from datetime import datetime
import logging
from fastapi.templating import Jinja2Templates
import traceback


from languia.utils import (
    EmptyResponseError,
    ContextTooLongError,
)  # Assuming these are defined elsewhere

from languia.litellm import litellm_stream_iter  # Assuming this is defined elsewhere

import time

import os

# from typing import Dict # Already imported Dict from typing
import json5

templates = Jinja2Templates(directory="templates")

app = FastAPI()
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

unavailable_models: Dict[str, Dict] = {}  # Explicitly typing

always_available_models = set(["o3-mini", "o4-mini", "grok-3-mini-beta", "qwen3-32b"])


stream_logs = logging.StreamHandler()
stream_logs.setLevel(logging.INFO)  # You might want to add this handler to a logger

tests: List[Dict] = []  # Explicitly typing

scheduled_tasks = set()

import litellm

litellm._turn_on_debug()


@app.get("/always_available_models/{model_id}/create", status_code=201)
@app.post("/always_available_models/{model_id}/create", status_code=201)
def create_always_available_models(model_id: str) -> bool:
    """
    Adds a model to the always_available_models set.
    If the model was in unavailable_models, it is removed from there.
    Returns True if the model was newly added, False if it was already there.
    """
    global always_available_models, unavailable_models
    if model_id not in always_available_models:
        always_available_models.add(model_id)  # Fixed: use model_id variable
        # If successfully added to always_available, remove from unavailable_models
        if model_id in unavailable_models:
            del unavailable_models[model_id]
            logging.info(
                f"Model {model_id} added to always_available_models and removed from unavailable_models."
            )
        else:
            logging.info(f"Model {model_id} added to always_available_models.")
        return True
    else:
        # If it's already in always_available, ensure it's not in unavailable just in case
        if model_id in unavailable_models:
            del unavailable_models[model_id]
            logging.info(
                f"Model {model_id} was already in always_available_models; ensured removal from unavailable_models."
            )
        else:
            logging.info(f"Model {model_id} is already in always_available_models.")
        return False


@app.get("/unavailable_models/{model_id}/create", status_code=201)
@app.post("/unavailable_models/{model_id}/create", status_code=201)
def disable_model(model_id: str, outage_details: dict = None) -> Union[Dict, bool]:
    """
    Manually disables a model by adding it to the unavailable_models list.
    A model cannot be disabled if it's in the always_available_models set.
    'outage_details' can be provided in the request body for POST.
    Returns the outage information if successful, False otherwise.
    """
    global unavailable_models
    if model_id not in always_available_models:
        logging.info(f"Force disabling model: {model_id}")
        outage = {
            "detection_time": datetime.now().isoformat(),
            "model_id": model_id,
            "reason": "Manual disable action.",  # Default reason
        }
        if outage_details:  # outage_details is the request body for POST
            outage.update(outage_details)

        unavailable_models[model_id] = outage
        return outage
    else:
        logging.warning(
            f"Attempted to disable model {model_id}, but it is in always_available_models."
        )
        return False


@app.get("/unavailable_models/")
def get_unavailable_models() -> List[str]:  # Return type hint
    return [model_id for model_id, _outage in unavailable_models.items()]


@app.get("/unavailable_models/{model_id}/delete", status_code=200)
@app.delete("/unavailable_models/{model_id}", status_code=200)
def remove_unavailable_models(
    model_id: str,
) -> Union[
    None, bool
]:  # FastAPI handles 204, actual return can be None or True/False for internal calls
    """Removes a model from the unavailable_models list."""
    if model_id in unavailable_models:
        del unavailable_models[model_id]
        logging.info(f"Model {model_id} removed from unavailable_models.")
        return True  # For internal calls or if a body is allowed with 204
    else:
        return False


@app.get("/always_available_models/{model_id}/delete", status_code=200)
@app.delete("/always_available_models/{model_id}", status_code=200)
def remove_always_available_models(model_id: str) -> Union[None, bool]:
    """Removes a model from the always_available_models set."""
    if model_id in always_available_models:
        always_available_models.remove(model_id)
        logging.info(f"Model {model_id} removed from always_available_models.")
        return True
    else:
        # return False


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
    "/unavailable_models/{model_id}"
)  # This path seems to be for testing a model, not getting its unavailability status
def test_model(model_id: str) -> Dict:
    """
    Tests a given model_id.
    Records the test result (incident) but does NOT automatically disable the model on failure.
    """
    global tests  # Ensure 'tests' is correctly typed List[Dict] globally
    if model_id == "None":  # Keep this check
        return {"success": False, "error_message": "Don't test 'None'!"}

    # Assuming get_endpoint is defined in languia.utils
    # from languia.utils import get_endpoint
    # Mocking get_endpoint for standalone execution, replace with your actual import
    def get_endpoint(m_id, ep_list=endpoints):
        for ep in ep_list:
            if ep.get("model_id") == m_id:
                return ep
        return None  # Or raise an error

    endpoint = get_endpoint(model_id)

    if not endpoint:
        logging.warning(f"Endpoint configuration not found for model_id: {model_id}")
        test_result = {
            "model_id": model_id,
            "timestamp": int(time.time()),
            "success": False,
            "message": f"Endpoint configuration not found for model_id: {model_id}",
        }
        tests.append(test_result)
        if len(tests) > 25:
            tests = tests[-25:]
        return test_result

    logging.info(f"Testing endpoint: {model_id}")

    temperature = 1
    max_new_tokens = 100

    text = ""  # Initialize text here

    try:
        model_name = endpoint.get("api_type", "openai") + "/" + endpoint["model_name"]

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
            max_new_tokens=max_new_tokens,  # Corrected from max_new_tokens=max_new_tokens
            vertex_ai_location=endpoint.get("vertex_ai_location", None),
            include_reasoning=include_reasoning,
            enable_reasoning=enable_reasoning,
        )

        output_tokens = None
        for data in stream_iter:
            if "output_tokens" in data:
                # print(f"reported output tokens for api {endpoint['api_id']}: " + str(data["output_tokens"])) # api_id might not exist
                logging.debug(
                    f"Reported output tokens for model {model_id}: {data['output_tokens']}"
                )
                output_tokens = data["output_tokens"]

            # Ensure 'output' is derived correctly
            current_chunk_text = data.get("text", data.get("reasoning"))
            if current_chunk_text:  # Accumulate text if streaming chunks
                text += current_chunk_text

        test_result = {  # Renamed from 'test' to 'test_result'
            "model_id": model_id,
            "timestamp": int(time.time()),
        }
        if output_tokens:
            test_result.update(output_tokens=output_tokens)

        # Success condition based on original logic
        # "Reasoning mode is broken" is handled by `include_reasoning` leading to success path.
        # `always_available_models` also leads to success path.
        if text or include_reasoning or model_id in always_available_models:
            logging.info(
                f"Test considered successful for: {model_id}. Received text: '{text}'"
            )

            # If it was previously unavailable and now works, remove it from unavailable_models
            if model_id in unavailable_models:  # Check before calling remove
                if remove_unavailable_models(
                    model_id
                ):  # remove_unavailable_models returns True on success
                    test_result.update(
                        {
                            "info": "Model was unavailable, now responding. Removed from unavailable_models list."
                        }
                    )

            test_result.update(
                {
                    "success": True,
                    "message": "Model responded: " + str(text),
                }
            )
            if (
                model_id in always_available_models
            ):  # This overrides the message if it's always available
                test_result.update(
                    {
                        "success": True,  # Ensures success is True
                        "message": f"Model is in always_available_models. Actual response: '{str(text)}'",
                    }
                )
        else:
            # This case means no text, not include_reasoning, and not in always_available_models
            # This would have raised EmptyResponseError before.
            reason = f"No content from model {model_id} and not covered by always_available/include_reasoning success conditions."
            logging.warning(
                f"Test issue: {reason}"
            )  # Log as warning, not error leading to disable
            test_result.update({"success": False, "message": reason})
            # DO NOT raise EmptyResponseError here to prevent it being caught by general exception and potentially misinterperted
            # The incident is recorded as success: False

        tests.append(test_result)
        if len(tests) > 25:
            tests = tests[-25:]
        return test_result

    except ContextTooLongError as e:  # Specific exception first
        logging.info(
            f"Test for {model_id} resulted in ContextTooLongError, considered as a valid (non-disabling) response for now."
        )
        test_result = {
            "model_id": model_id,
            "timestamp": int(time.time()),
            "success": True,  # As per original logic for this error
            "message": f"Model test triggered ContextTooLongError: {str(e)}",
        }
        # If it was previously unavailable, remove it because it's "responding" in a way
        if model_id in unavailable_models:
            if remove_unavailable_models(model_id):
                test_result.update(
                    {
                        "info": "Model was unavailable, now responding (ContextTooLongError). Removed from unavailable_models list."
                    }
                )
        tests.append(test_result)
        # Trim tests list
        if len(tests) > 25:
            tests = tests[-25:]
        return test_result

    except Exception as e:
        reason = str(e)
        logging.error(
            f"Error during test for model {model_id}: {reason}", exc_info=False
        )  # exc_info=True if full stack trace needed in logs
        stacktrace_str = traceback.format_exc()  # Corrected: get stacktrace as string

        test_result = {
            "model_id": model_id,
            "timestamp": int(time.time()),
            "success": False,
            "message": reason,
            "stacktrace": stacktrace_str,
        }

        # DO NOT DISABLE THE MODEL AUTOMATICALLY
        # # Old line: disable_model(model_id, test_result) # This line is now removed.

        tests.append(test_result)
        if len(tests) > 25:
            tests = tests[-25:]
        return test_result


@app.get(
    "/",
    response_class=HTMLResponse,
)
def index(request: Request, scheduled_tests: bool = False):
    global tests
    # Sort tests by timestamp descending (newest first) for display
    sorted_tests = sorted(tests, key=lambda x: x.get("timestamp", 0), reverse=True)
    return templates.TemplateResponse(
        "unavailable_models.html",
        {
            "tests": sorted_tests,  # Use sorted tests
            "unavailable_models": unavailable_models,
            "always_available_models": always_available_models,
            "endpoints": endpoints,
            "request": request,
            "scheduled_tests": scheduled_tests,
            "now": int(time.time()),
        },
    )


@app.get("/test_all_endpoints")
def test_all_endpoints(background_tasks: BackgroundTasks) -> RedirectResponse:
    """
    Initiates background tasks to test all models asynchronously.
    Only tests models not in always_available_models as per original logic.
    """
    tested_count = 0
    for (
        endpoint_config
    ) in endpoints:  # Renamed 'endpoint' to 'endpoint_config' to avoid conflict
        model_id_to_test = endpoint_config.get("model_id")
        if model_id_to_test:  # Ensure model_id exists
            # The original logic was: if endpoint.get("model_id") not in always_available_models:
            # This meant 'always_available_models' were not part of the scheduled bulk tests.
            # Keeping this behavior unless specified otherwise.
            # If you want to test all models including always_available ones, remove this condition.
            if model_id_to_test not in always_available_models:
                try:
                    background_tasks.add_task(test_model, model_id_to_test)
                    tested_count += 1
                except Exception as e:  # Catch potential errors during task scheduling
                    logging.error(
                        f"Failed to schedule test for model {model_id_to_test}: {e}"
                    )
            else:
                logging.info(
                    f"Skipping scheduled test for {model_id_to_test} as it is in always_available_models."
                )
        else:
            logging.warning(
                f"Endpoint configuration found without a model_id: {endpoint_config}"
            )

    logging.info(f"Scheduled {tested_count} models for testing.")
    return RedirectResponse(url="/?scheduled_tests=true", status_code=302)


# async def periodic_test_all_endpoints():
# """
# Periodically test a model in the background.
# """
# while True:
# logging.info("Periodic testing models")
# test_all_endpoints() # This function itself is not async and returns a RedirectResponse
#                     # For periodic tasks, you'd call the logic directly or refactor test_all_endpoints
#                     # to not return a RedirectResponse when called internally.
# await asyncio.sleep(3600) # Test every hour


# @app.on_event("startup")
# async def start_periodic_tasks():
# # Schedule the periodic model testing task
# asyncio.create_task(periodic_test_all_endpoints())

# Example of how languia.utils might look (MOCK for testing):
# class EmptyResponseError(Exception): pass
# class ContextTooLongError(Exception): pass
# def get_endpoint(model_id, ep_list=None):
#     if ep_list is None: ep_list = []
#     for ep in ep_list:
#         if ep.get("model_id") == model_id:
#             return ep
#     return None
