"""
LiteLLM integration for unified API communication.

This module provides a unified interface to call different LLM APIs (OpenAI, Google Vertex AI,
OpenRouter, etc.) through LiteLLM, handling streaming responses, token counting, and error handling.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Generator, Union, cast

import litellm

from backend.config import (
    GLOBAL_TIMEOUT,
    ORDBOGEN_GLOBAL_TIMEOUT,
    ORDBOGEN_STREAM_TIMEOUT,
    STREAM_TIMEOUT,
    settings,
)
from backend.errors import ContextTooLongError

if TYPE_CHECKING:
    from fastapi import Request

    from backend.llms.models import Endpoint, LLMDataEnabled
    from utils.database.models import AnyMessageRead, LLMMessageCreate

logger = logging.getLogger("languia")


def get_api_key(endpoint: "Endpoint") -> str | None:
    """
    Get the appropriate API key for an endpoint.

    Different providers require different API keys:
    - Albert (French LLM): ALBERT_KEY
    - HuggingFace Inference: HF_INFERENCE_KEY
    - OpenRouter/Vertex: handled by LiteLLM from env variables

    Args:
        endpoint: Endpoint configuration dict with api_base

    Returns:
        str: API key, or None if using standard provider (OpenRouter/Vertex)
    """
    # Albert is French government LLM
    # "api_base": "https://albert.api.etalab.gouv.fr/v1/",

    # "api_type": "huggingface/cohere" doesn't work, using the openai api type and api_base="https://router.huggingface.co/cohere/compatibility/v1/"
    if endpoint.api_base and "albert.api.etalab.gouv.fr" in endpoint.api_base:
        return settings.ALBERT_KEY
    # HuggingFace Inference API
    if endpoint.api_base and "huggingface.co" in endpoint.api_base:
        return settings.HF_INFERENCE_KEY
    # Ordbogen.ai (Danish LLM)
    if endpoint.api_base and "ordbogen.ai" in endpoint.api_base:
        return settings.ORDBOGEN_API_KEY
    # OpenRouter is handled by LiteLLM reading OPENROUTER_API_KEY env variable directly
    return None


def litellm_stream_iter(
    llm: "LLMDataEnabled",
    messages: list["AnyMessageRead"],
    msg: "LLMMessageCreate",
    temperature: float,
    max_new_tokens: int,
    request: Union["Request", None] = None,
    include_reasoning: bool = False,  # FIXME Legacy ?
    enable_reasoning: bool = False,  # FIXME Legacy ?
) -> Generator["LLMMessageCreate"]:
    """
    Stream responses from an LLM API using LiteLLM.

    This function handles unified API calls to various LLM providers through LiteLLM,
    manages streaming responses, and processes tokens and metadata.

    Args:
        llm: LLM data
        messages: List of messages to be serialized for llm call
        msg: initialized LLMMessageCreate to update
        temperature: Sampling temperature for response diversity
        max_new_tokens: Maximum tokens to generate
        request: FastAPI request for logging
        include_reasoning: Whether to include reasoning in response
        enable_reasoning: Whether to enable reasoning mode

    Yields:
        updated LLMMessageCreate
    """
    endpoint = llm.endpoint
    # Build LiteLLM model identifier (e.g., "openai/gpt-4", "google/gemini-pro")
    litellm_model_name = f"{endpoint.api_type}/{endpoint.api_model_id}"
    # Retrieve API key from environment or config
    api_key = get_api_key(endpoint)

    logger.info(
        f"using endpoint {litellm_model_name} for {llm.id}: {endpoint.model_dump(mode="json")}",
        extra={"request": request},
    )

    # Debug mode can be enabled but is very verbose for streaming
    # from backend.config import debug
    # if debug:
    #     litellm._turn_on_debug()

    # Configure Sentry error tracking if available
    if settings.SENTRY_DSN:
        litellm.input_callback = ["sentry"]  # adds sentry breadcrumbing
        litellm.failure_callback.append("sentry")

    # nice to have: openrouter specific params
    # completion = client.chat.completions.create(
    #   extra_headers={
    #     "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
    #     "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
    #   },

    is_ordbogen = endpoint.api_base and "ordbogen.ai" in endpoint.api_base

    # Build parameters for LiteLLM API call
    kwargs = {
        "timeout": ORDBOGEN_GLOBAL_TIMEOUT if is_ordbogen else GLOBAL_TIMEOUT,
        "stream_timeout": ORDBOGEN_STREAM_TIMEOUT if is_ordbogen else STREAM_TIMEOUT,
        "api_version": endpoint.api_version,
        "base_url": endpoint.api_base,
        "api_key": api_key,
        # max_retries can be added if needed
        "model": litellm_model_name,
        # Only pass supported message args 'role' and 'content'
        "messages": [msg.model_dump(include={"role", "content"}) for msg in messages],
        "temperature": temperature,
        "max_tokens": max_new_tokens,
        "stream": True,  # Enable streaming for real-time responses
    }

    # Use mock response for testing if enabled
    if settings.MOCK_RESPONSE:
        logger.warning(f"MOCK_RESPONSE enabled")
        kwargs["mock_response"] = (
            "This is a fake response that didn't contact the LLM api."
        )

    # Request token usage reporting (except for Aya which doesn't support it)
    if "c4ai-aya-expanse-32b" not in litellm_model_name:
        kwargs["stream_options"] = {"include_usage": True}

    # Enable extended reasoning (e.g., o1 models)
    if include_reasoning:
        kwargs["include_reasoning"] = True

    # Some models support enable_reasoning mode
    if enable_reasoning:
        kwargs["enable_reasoning"] = True

    # Store call start ts
    msg.created_at = datetime.now()

    # Make the API call through LiteLLM
    try:
        response: Generator[litellm.ModelResponse] = litellm.completion(**kwargs)
    except litellm.ContextWindowExceededError as e:
        logger.error(
            f"context_window_exceeded: {litellm_model_name}: {e}",
            extra={"request": request},
        )
        raise ContextTooLongError from e

    # OpenRouter specific params could be added here
    # transforms = [""], route= ""

    # Process streaming chunks from the API
    for chunk in response:
        if not msg.responded_at:
            # Store first chunk ts for latency computation
            msg.responded_at = datetime.now()
        # Extract generation ID for tracking/debugging
        if not msg.generation_id and chunk.id:
            msg.generation_id = chunk.id
            logger.debug(
                f"Response stream started for '{litellm_model_name}' with generation_id='{chunk.id}'",
                extra={"request": request},
            )
        # Extract token count from streaming completion (if available)
        if hasattr(chunk, "usage") and hasattr(chunk.usage, "completion_tokens"):
            msg.tokens = chunk.usage.completion_tokens
            logger.debug(
                f"reported output tokens for api {endpoint.api_base} and model {litellm_model_name}: {msg.tokens}",
                extra={"request": request},
            )
        # Process content chunks
        if len(chunk.choices) > 0:
            choice = cast(litellm.types.utils.StreamingChoices, chunk.choices[0])

            # Accumulate text and reasoning across chunks
            if delta := choice.get("delta"):
                # Get the text content of this chunk
                if content := choice.delta.get("content"):
                    msg.content += content
                # Get reasoning content (for reasoning models)
                if reasoning := delta.get("reasoning_content") or delta.get(
                    "reasoning"
                ):
                    msg.reasoning_content += reasoning

            # Check for generation completion signal
            if choice.finish_reason == "stop":
                break
            elif choice.finish_reason == "length":
                # Output truncated at max_tokens limit — response is still valid
                logger.warning(
                    "output_truncated_at_max_tokens: " + str(chunk),
                    extra={"request": request},
                )
                break

            # Yield partial results for streaming to frontend
            yield msg

    # Store last update ts for duration computation
    msg.updated_at = datetime.now()

    logger.debug(
        f"Response stream ended for '{litellm_model_name}' with generation_id='{chunk.id}'",
        extra={"request": request},
    )

    # Final yield after loop completes
    yield msg
