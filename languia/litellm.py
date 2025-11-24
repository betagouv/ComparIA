"""
Utilities to communicate with different APIs
"""

import os
import logging

from languia.config import GLOBAL_TIMEOUT
import litellm
import json

from languia.utils import strip_metadata, ContextTooLongError

# from langfuse import get_client, observe

if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    with open(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), "r") as file:
        vertex_credentials = json.load(file)
        vertex_credentials_json = json.dumps(vertex_credentials)
else:
    logger = logging.getLogger("languia")
    logger.warning("No Google creds detected!")
    vertex_credentials_json = None


# @observe(as_type="generation")
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
    enable_reasoning=False,
):

    # Too verbose:
    # from languia.config import debug
    # if debug:
    #     litellm._turn_on_debug()

    if os.getenv("SENTRY_DSN"):
        litellm.input_callback = ["sentry"]  # adds sentry breadcrumbing
        litellm.failure_callback.append("sentry")

    if vertex_ai_location:
        litellm.vertex_location = vertex_ai_location
    else:
        litellm.vertex_location = os.getenv("VERTEXAI_LOCATION", None)

    # nice to have: openrouter specific params
    # completion = client.chat.completions.create(
    #   extra_headers={
    #     "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
    #     "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
    #   },

    # Not ready yet, see https://github.com/BerriAI/litellm/issues/11742
    # if (
    #     os.getenv("LANGFUSE_PUBLIC_KEY")
    #     and os.getenv("LANGFUSE_SECRET_KEY")
    #     # os.getenv("LANGFUSE_HOST") is optional (sent to SaaS if unset)
    # ):
    #     litellm.success_callback = ["langfuse_otel"]
    #     litellm.failure_callback.append("langfuse_otel")

    # Update langfuse trace explicitly
    # user_id, session_id = get_user_info(request)
    # langfuse = get_client()
    # langfuse.update_current_trace(
    #     user_id=user_id,
    #     session_id=session_id,
    # )

    messages = strip_metadata(messages)
    logging.debug("stripping metadata")

    # Check for mock response environment variable
    mock_response = os.getenv("MOCK_RESPONSE")
    if mock_response:
        logger = logging.getLogger("languia")
        logger.warning(f"MOCK_RESPONSE enabled with value: {mock_response}")

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
        # manually add langfuse span/trace metadata, see https://github.com/langfuse/langfuse/issues/2238
        # "metadata": {
        # "trace_user_id": user_id,
        # "session_id": session_id,
        # "langfuse_parent_observation_id": span.id,
        # "langfuse_trace_id": span.trace_id,
        # "trace_id": span.trace_id,
        # "parent_span_id": span.id,
        # "existing_trace_id": span.trace_id,
        # "parent_observation_id": span.id,
        # "generation_id": span.id
        # },
    }

    if mock_response:
        kwargs["mock_response"] = mock_response

    if "c4ai-aya-expanse-32b" not in model_name:
        kwargs["stream_options"] = {"include_usage": True}

    if include_reasoning:
        kwargs["include_reasoning"] = True

    if enable_reasoning:
        kwargs["enable_reasoning"] = True

    res = litellm.completion(**kwargs)

    # openrouter specific params
    # transforms = [""],
    # route= ""

    text = ""
    reasoning = ""
    logger = logging.getLogger("languia")

    data = dict()

    for i, chunk in enumerate(res):
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
                reasoning_delta = ""
                if hasattr(chunk.choices[0].delta, "content"):
                    content = chunk.choices[0].delta.content or ""
                else:
                    content = ""
                if hasattr(chunk.choices[0].delta, "reasoning"):
                    reasoning_delta = chunk.choices[0].delta.reasoning or ""
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
                    logger.error(
                        "context_too_long: " + str(chunk), extra={request: request}
                    )
                    raise ContextTooLongError

            yield data
    yield data
