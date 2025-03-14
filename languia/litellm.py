"""
Utilities to communicate with different APIs
"""

import os
import logging

import sentry_sdk

from gradio import Error

from languia.config import GLOBAL_TIMEOUT
import litellm
import json

from langfuse.decorators import langfuse_context, observe

if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    with open(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), "r") as file:
        vertex_credentials = json.load(file)
        vertex_credentials_json = json.dumps(vertex_credentials)
else:
    logger = logging.getLogger("languia")
    logger.warn("No Google creds detected!")
    vertex_credentials_json = None


@observe()
def litellm_stream_iter(
    model_name,
    messages,
    temperature,
    max_new_tokens,
    api_base=None,
    api_key=None,
    request=None,
    api_version=None,
    vertex_ai_location=None,
    include_reasoning=False
):

    from languia.config import debug

    # Too verbose:
    # if debug:
    #     litellm._turn_on_debug()

    if (
        os.getenv("LANGFUSE_PUBLIC_KEY")
        and os.getenv("LANGFUSE_SECRET_KEY")
        # os.getenv("LANGFUSE_HOST") is optional (sent to SaaS if unset)
    ):
        print("loading langfuse")
        litellm.success_callback = ["langfuse"]
        litellm.failure_callback.append("langfuse")
    if os.getenv("SENTRY_DSN"):
        litellm.input_callback = ["sentry"]  # adds sentry breadcrumbing
        litellm.failure_callback.append("sentry")

    if not vertex_ai_location and os.getenv("VERTEXAI_LOCATION"):
        litellm.vertex_location = os.getenv("VERTEXAI_LOCATION")
    else:
        litellm.vertex_location = vertex_ai_location

    # TODO: openrouter specific params
    # completion = client.chat.completions.create(
    #   extra_headers={
    #     "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
    #     "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
    #   },
    
    kwargs = {
        "api_version": api_version,
        "timeout": GLOBAL_TIMEOUT,
        "stream_timeout": 30,
        "base_url": api_base,
        "api_key": api_key,
        # max_retries=
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_new_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
        "vertex_credentials": vertex_credentials_json,
        "vertex_ai_location": litellm.vertex_location,
        "metadata": {
            "session_hash": getattr(request, "session_hash", ""),
            # "conversation_id
            # Creates nested traces for convos A and B
            # "existing_trace_id": langfuse_context.get_current_trace_id(),
            "parent_observation_id": langfuse_context.get_current_observation_id(),
        },
    }

    if include_reasoning:
        kwargs["include_reasoning"] = True

    res = litellm.completion(**kwargs)

    # openrouter specific params
    # transforms = [""],
    # route= ""

    text = ""
    logger = logging.getLogger("languia")

    data = dict()

    for chunk in res:
        if hasattr(chunk, "id"):
            data["generation_id"] = chunk.id
            logger.debug(
                f"generation_id: {chunk.id} for api {api_base} and model {model_name}",
                extra={"request": request},
            )
        if hasattr(chunk, "usage") and hasattr(chunk.usage, "completion_tokens"):
            data["output_tokens"] = chunk.usage.completion_tokens
            logger.debug(
                f"reported output tokens for api {api_base} and model {model_name}: "
                + str(data["output_tokens"]),
                extra={"request": request},
            )
        if hasattr(chunk, "choices") and len(chunk.choices) > 0:
            if hasattr(chunk.choices[0], "delta"):
                if hasattr(chunk.choices[0].delta, "content"):
                    content = chunk.choices[0].delta.content or ""
                else:
                    content = ""
                # TODO: extract thinking here / pass to frontend / wrap into <think> tags
                if hasattr(chunk.choices[0].delta, "reasoning"):
                    print("GOT REASONING")
                    content = chunk.choices[0].delta.reasoning or ""
            else:
                content = ""

            text += content

            data["text"] = text

            if hasattr(chunk.choices[0], "finish_reason"):
                if chunk.choices[0].finish_reason == "stop":
                    data["text"] = text
                    break
                elif chunk.choices[0].finish_reason == "length":
                    # cannot raise ContextTooLong because sometimes the model stops only because of current answer's (output) length limit, e.g. HuggingFace free API w/ Phi
                    # raise ContextTooLongError
                    logger.warning(
                        "context_too_long: " + str(chunk), extra={request: request}
                    )

                    if os.getenv("SENTRY_DSN"):
                        sentry_sdk.capture_message(f"context_too_long: {chunk}")
                    break
            # Special handling for certain models
            # if model_name == "meta/llama3-405b-instruct-maas" or model_name == "google/gemini-1.5-pro-001":
            yield data
    yield data
