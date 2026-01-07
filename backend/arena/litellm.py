"""
LiteLLM integration for unified API communication.

This module provides a unified interface to call different LLM APIs (OpenAI, Google Vertex AI,
OpenRouter, etc.) through LiteLLM, handling streaming responses, token counting, and error handling.
"""

import json
import logging
import os
from typing import Generator

import litellm

from backend.arena.utils import ContextTooLongError
from backend.config import GLOBAL_TIMEOUT

# Load Google Cloud credentials for Vertex AI if available
if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    with open(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), "r") as file:
        vertex_credentials = json.load(file)
        vertex_credentials_json = json.dumps(vertex_credentials)
else:
    logger = logging.getLogger("languia")
    logger.warning("No Google creds detected!")
    vertex_credentials_json = None


def litellm_stream_iter(
    model_name,
    messages,
    temperature,
    max_new_tokens,
    api_base=None,
    api_key=None,
    ip=None,
    api_version=None,
    vertex_ai_location=None,
    include_reasoning=False,
    enable_reasoning=False,
) -> Generator:
    """
    Stream responses from an LLM API using LiteLLM.

    This function handles unified API calls to various LLM providers through LiteLLM,
    manages streaming responses, and processes tokens and metadata.

    Args:
        model_name: Model identifier in LiteLLM format (e.g., "openai/gpt-4")
        messages: List of message dicts with role/content
        temperature: Sampling temperature for response diversity
        max_new_tokens: Maximum tokens to generate
        api_base: Optional API base URL override
        api_key: API key for the provider
        ip: Client IP address for logging context
        api_version: Optional API version (e.g., for Azure)
        vertex_ai_location: Google Vertex AI region
        include_reasoning: Whether to include reasoning in response
        enable_reasoning: Whether to enable reasoning mode

    Yields:
        Dict containing: text, reasoning, output_tokens, generation_id
    """

    # Debug mode can be enabled but is very verbose for streaming
    # from backend.config import debug
    # if debug:
    #     litellm._turn_on_debug()

    # Configure Sentry error tracking if available
    if os.getenv("SENTRY_DSN"):
        litellm.input_callback = ["sentry"]  # adds sentry breadcrumbing
        litellm.failure_callback.append("sentry")

    # Set Vertex AI location for Google Cloud models
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

    # Check for mock response environment variable (useful for testing/demo)
    mock_response = os.getenv("MOCK_RESPONSE")
    if mock_response:
        logger = logging.getLogger("languia")
        logger.warning(f"MOCK_RESPONSE enabled")

    # Build parameters for LiteLLM API call
    kwargs = {
        "api_version": api_version,
        "timeout": GLOBAL_TIMEOUT,
        "stream_timeout": 30,
        "base_url": api_base,
        "api_key": api_key,
        # max_retries can be added if needed
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_new_tokens,
        "stream": True,  # Enable streaming for real-time responses
        "vertex_credentials": vertex_credentials_json,
        "vertex_ai_location": litellm.vertex_location,
    }

    # Use mock response for testing if enabled
    if mock_response:
        kwargs["mock_response"] = (
            "This is a fake response that didn't contact the LLM api."
        )

    # Request token usage reporting (except for Aya which doesn't support it)
    if "c4ai-aya-expanse-32b" not in model_name:
        kwargs["stream_options"] = {"include_usage": True}

    # Enable extended reasoning (e.g., o1 models)
    if include_reasoning:
        kwargs["include_reasoning"] = True

    # Some models support enable_reasoning mode
    if enable_reasoning:
        kwargs["enable_reasoning"] = True

    # Make the API call through LiteLLM
    res = litellm.completion(**kwargs)

    # OpenRouter specific params could be added here
    # transforms = [""], route= ""

    # Initialize accumulators for streaming response
    text = ""
    reasoning = ""
    logger = logging.getLogger("languia")

    # Data dict to accumulate response metadata
    data = dict()

    # Process streaming chunks from the API
    for chunk in res:
        # Extract generation ID for tracking/debugging
        if hasattr(chunk, "id"):
            data["generation_id"] = chunk.id
            logger.debug(
                f"generation_id: {chunk.id} for api {api_base} and model {model_name}",
                extra={"ip": ip},
            )
        # Extract token count from streaming completion (if available)
        if hasattr(chunk, "usage") and hasattr(chunk.usage, "completion_tokens"):
            data["output_tokens"] = chunk.usage.completion_tokens
            logger.debug(
                f"reported output tokens for api {api_base} and model {model_name}: "
                + str(data["output_tokens"]),
                extra={"ip": ip},
            )
        # Process content chunks
        if hasattr(chunk, "choices") and len(chunk.choices) > 0:
            # Extract delta content and reasoning from chunk
            if hasattr(chunk.choices[0], "delta"):
                reasoning_delta = ""
                # Get the text content of this chunk
                if hasattr(chunk.choices[0].delta, "content"):
                    content = chunk.choices[0].delta.content or ""
                else:
                    content = ""
                # Get reasoning content (for reasoning models)
                if hasattr(chunk.choices[0].delta, "reasoning"):
                    reasoning_delta = chunk.choices[0].delta.reasoning or ""
            else:
                content = ""

            # Accumulate text and reasoning across chunks
            text += content
            reasoning += reasoning_delta
            data["reasoning"] = reasoning
            data["text"] = text

            # Check for generation completion signal
            if hasattr(chunk.choices[0], "finish_reason"):
                if chunk.choices[0].finish_reason == "stop":
                    data["text"] = text
                    break
                elif chunk.choices[0].finish_reason == "length":
                    # Model hit max tokens limit
                    logger.error("context_too_long: " + str(chunk), extra={"ip": ip})
                    raise ContextTooLongError

            # Yield partial results for streaming to frontend
            yield data
    # Final yield after loop completes
    yield data
