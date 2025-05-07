"""
Utilities to communicate with different APIs
"""

import os
import logging

import sentry_sdk

from languia.config import GLOBAL_TIMEOUT
import litellm
import json

from languia.utils import strip_metadata, get_user_info

from langfuse.decorators import langfuse_context, observe

if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    with open(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), "r") as file:
        vertex_credentials = json.load(file)
        vertex_credentials_json = json.dumps(vertex_credentials)
else:
    logger = logging.getLogger("languia")
    logger.warn("No Google creds detected!")
    vertex_credentials_json = None


@observe(as_type="generation")
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
    include_reasoning=False,
):

    # Too verbose:
    # from languia.config import debug
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

    # nice to have: openrouter specific params
    # completion = client.chat.completions.create(
    #   extra_headers={
    #     "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
    #     "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
    #   },
    
    
    user_id, session_id = get_user_info(request)
    langfuse_context.update_current_trace(
            user_id=user_id,
            session_id=session_id,
        #     metadata={
        #     "parent_observation_id": langfuse_context.get_current_observation_id(),
        #     "trace_user_id": user_id,
        #     "session_id": session_id,      
        #     # Creates nested traces for convos A and B
        #     "existing_trace_id": langfuse_context.get_current_trace_id(),
        # },
        )
    if "mistralai" in model_name:
        messages = strip_metadata(messages)
        print("stripping metadata")
        
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
        "vertex_credentials": vertex_credentials_json,
        "vertex_ai_location": litellm.vertex_location,
        # "metadata": {
        #     "parent_observation_id": langfuse_context.get_current_observation_id(),
        #     "trace_user_id": user_id,
        #     "session_id": session_id,      
        #     # Creates nested traces for convos A and B
        #     "existing_trace_id": langfuse_context.get_current_trace_id(),
        # },
    }

    if "c4ai-aya-expanse-32b" not in model_name:
        kwargs["stream_options"] = {"include_usage": True}

    if include_reasoning:
        kwargs["include_reasoning"] = True

    res = litellm.completion(**kwargs)

    # openrouter specific params
    # transforms = [""],
    # route= ""

    text = ""
    reasoning = ""
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
                if hasattr(chunk.choices[0].delta, "reasoning"):
                    reasoning_delta = chunk.choices[0].delta.reasoning or ""
                else:
                    reasoning_delta = ""
            else:
                content = ""

            text += content
            reasoning += reasoning_delta
            data["reasoning"] = reasoning
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
