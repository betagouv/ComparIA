"""
Utilities to communicate with different APIs
"""

import os
import logging

import sentry_sdk

from gradio import Error

from languia.config import GLOBAL_TIMEOUT
import litellm

def get_api_provider_stream_iter(
    messages,
    model_api_dict,
    temperature,
    max_new_tokens,
    request=None,
):
    messages_dict = []
    for message in messages:
        try:
            messages_dict.append({"role": message.role, "content": message.content})
        except:
            raise TypeError(f"Expected ChatMessage object, got {type(message)}")

    litellm_model_name = (
        model_api_dict.get("api_type", "openai")
        + "/"
        + model_api_dict["model_name"]
    )
    stream_iter = litellm_stream_iter(
        model_name=litellm_model_name,
        messages=messages_dict,
        temperature=temperature,
        api_key=model_api_dict.get("api_key", "F4K3-4P1-K3Y"),
        api_base=model_api_dict.get("api_base", None),
        api_version=model_api_dict.get("api_version", None),
        # stream=model_api_dict.get("stream", True),
        # top_p=top_p,
        max_new_tokens=max_new_tokens,
        request=request,
    )

    return stream_iter


def process_response_stream(response, model_name=None, api_base=None, request=None):
    """
    Processes the stream of responses from the OpenAI API.
    """
    text = ""
    logger = logging.getLogger("languia")

    data = dict()
    buffer = ""
    import random

    # def barrel_roll():
    #     if random.random() < 1/200:
    #         raise Error("*BANG!*")
    #     else:
    #         return "No explosion"


    for chunk in response:
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


    res = litellm.completion(api_version=api_version,
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
        # Not available like this
        # top_p=top_p,
        
    )
    # print(res.dict())
    yield from process_response_stream(
        res, model_name=model_name, api_base=api_base, request=request
    )


def vertex_api_stream_iter(
    api_base, model_name, messages, temperature, max_new_tokens, request=None
):
    logger = logging.getLogger("languia")

    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        import json
        with open(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), 'r') as file:
            vertex_credentials = json.load(file)
            vertex_credentials_json = json.dumps(vertex_credentials)
    else:
        logger.warn("No Google creds detected!")

    res = litellm.completion(
        timeout=GLOBAL_TIMEOUT,
        model="vertex_ai/" + model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_new_tokens,
        # vertex_ai_project=litellm.vertex_project,
        # vertex_ai_location=litellm.vertex_location,
        # base_url=api_base,
        # api_key=creds.token,
        vertex_credentials=vertex_credentials_json,
        stream=True,
        stream_options={"include_usage": True},
    )
    yield from process_response_stream(res, model_name=model_name, request=request)
