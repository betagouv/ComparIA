"""
Utilities to communicate with different APIs
"""

import os
import logging

import sentry_sdk

from gradio import Error

from languia.config import GLOBAL_TIMEOUT
import litellm

from languia.utils import Timeout

if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    import json
    with open(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), 'r') as file:
        vertex_credentials = json.load(file)
        vertex_credentials_json = json.dumps(vertex_credentials)
else:
    logger = logging.getLogger("languia")
    logger.warn("No Google creds detected!")


def litellm_stream_iter(
    model_name,
    messages,
    temperature,
    max_new_tokens,
    api_base=None,
    api_key=None,
    request=None,
    api_version=None,
):

    from languia.config import debug

    # Too verbose:
    # if debug:
    #     litellm.set_verbose=True

    if os.getenv("SENTRY_DSN"):
        litellm.input_callback = ["sentry"]  # adds sentry breadcrumbing
        litellm.failure_callback = [
            "sentry"
        ]  # [OPTIONAL] if you want litellm to capture -> send exception to sentry

    if os.getenv("VERTEXAI_LOCATION"):
        litellm.vertex_location = os.getenv("VERTEXAI_LOCATION")
        
    res = litellm.completion(
        api_version=api_version,
        timeout=GLOBAL_TIMEOUT,
        base_url=api_base,
        api_key=api_key,
        # max_retries=
        model=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_new_tokens,
        stream=True,
        stream_options={"include_usage": True},
        vertex_credentials=vertex_credentials_json,
        vertex_ai_location=litellm.vertex_location
        # Not available like this
        # top_p=top_p,
    )

    text = ""
    logger = logging.getLogger("languia")

    data = dict()
    buffer = ""

    # def barrel_roll():
    #     import random
    #     import time
    #     if random.random() < 1/50:
    #         print("Sleeping 15s...")
    #         time.sleep(15)
    #         # raise Error("*BANG!*")
    #     else:
    #         return "No explosion"

    for chunk in res:
        with Timeout(10):
            # print(barrel_roll())
            if hasattr(chunk, "usage") and hasattr(chunk.usage, "completion_tokens"):
                data["output_tokens"] = chunk.usage.completion_tokens
                logger.debug(
                    f"reported output tokens for api {api_base} and model {model_name}: "
                    + str(data["output_tokens"])
                )
            if hasattr(chunk, "choices") and len(chunk.choices) > 0:
                if hasattr(chunk.choices[0], "delta") and hasattr(
                    chunk.choices[0].delta, "content"
                ):
                    content = chunk.choices[0].delta.content or ""
                else:
                    content = ""

                text += content
                buffer += content

                data["text"] = text

                if hasattr(chunk.choices[0], "finish_reason"):
                    if chunk.choices[0].finish_reason == "stop":
                        data["text"] = text
                        break
                    elif chunk.choices[0].finish_reason == "length":
                        # cannot raise ContextTooLong because sometimes the model stops only because of current answer's (output) length limit, e.g. HuggingFace free API w/ Phi
                        # raise ContextTooLongError
                        logger.warning("context_too_long: " + str(chunk))

                        if os.getenv("SENTRY_DSN"):
                            sentry_sdk.capture_message(f"context_too_long: {chunk}")
                        break
                # Special handling for certain models
                # if model_name == "meta/llama3-405b-instruct-maas" or model_name == "google/gemini-1.5-pro-001":

            if len(buffer.split()) >= 30:
                # if "\n" in buffer or "." in buffer:

                # Reset word count after yielding
                buffer = ""

                yield data
    yield data
