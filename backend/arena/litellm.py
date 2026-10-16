"""
LiteLLM integration for unified API communication.

This module provides a unified interface to call different LLM APIs (OpenAI, Google Vertex AI,
OpenRouter, etc.) through LiteLLM, handling streaming responses, token counting, and error handling.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, AsyncGenerator, Union, cast

import litellm

# litellm imports the provider client lazily, several hundred modules, on the
# first call. Loaded here, at startup, it no longer freezes the event loop
# for every visitor during a worker's first comparison.
import openai.resources  # noqa: F401

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

    from backend.arena.conversation import AnyMessageRead
    from backend.llms.models import LLMDataEnabled
    from utils.database.models import LLMMessageCreate

logger = logging.getLogger("languia")

MOCK_ANSWER = "This is a fake response that didn't contact the LLM api."


def mock_answer(chars: int) -> str:
    """The fake answer, repeated or cut to exactly `chars` characters."""
    if not chars:
        return MOCK_ANSWER
    repeats = chars // (len(MOCK_ANSWER) + 1) + 1
    return " ".join([MOCK_ANSWER] * repeats)[:chars]


def litellm_messages(messages: list["AnyMessageRead"]) -> list[dict[str, Any]]:
    """What a model is sent: each message's role and content only, with the
    web search results merged into the prompt they came with."""
    return [
        msg.model_dump(include={"role", "content"}, context={"merge_web_search": True})
        for msg in messages
    ]


def sent_chars(messages: list["AnyMessageRead"]) -> int:
    return sum(len(msg["content"] or "") for msg in litellm_messages(messages))


async def litellm_stream_iter(
    llm: "LLMDataEnabled",
    messages: list["AnyMessageRead"],
    msg: "LLMMessageCreate",
    temperature: float,
    max_new_tokens: int,
    request: Union["Request", None] = None,
    include_reasoning: bool = False,  # FIXME Legacy ?
    enable_reasoning: bool = False,  # FIXME Legacy ?
) -> AsyncGenerator["LLMMessageCreate"]:
    """
    Stream responses from an LLM API using LiteLLM.

    Every read from the provider is awaited, so a slow model only slows the
    comparison it answers and the event loop keeps serving everyone else.

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
    endpoint = llm.litellm_endpoint

    logger.info(
        f"using endpoint {endpoint.model} for {llm.id}: {endpoint.model_dump(mode="json", exclude={"api_key"})}",
        extra={"request": request},
    )

    # Debug mode can be enabled but is very verbose for streaming
    # from backend.config import debug
    # if debug:
    #     litellm._turn_on_debug()

    # No input_callback here: it would ship every raw prompt to Sentry as a
    # breadcrumb. Failures are reported explicitly via sentry_sdk.capture_exception
    # elsewhere instead of the litellm failure_callback, which also carries the
    # request body.

    # nice to have: openrouter specific params
    # completion = client.chat.completions.create(
    #   extra_headers={
    #     "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
    #     "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
    #   },

    is_ordbogen = endpoint.base_url and "ordbogen.ai" in endpoint.base_url

    # Build parameters for LiteLLM API call
    kwargs = {
        "timeout": ORDBOGEN_GLOBAL_TIMEOUT if is_ordbogen else GLOBAL_TIMEOUT,
        "stream_timeout": ORDBOGEN_STREAM_TIMEOUT if is_ordbogen else STREAM_TIMEOUT,
        # litellm endpoint formated args
        **endpoint.model_dump(),
        # max_retries can be added if needed
        "messages": litellm_messages(messages),
        "temperature": temperature,
        "max_tokens": max_new_tokens,
        "stream": True,  # Enable streaming for real-time responses
    }

    # Use mock response for testing if enabled
    if settings.MOCK_RESPONSE:
        logger.warning(f"MOCK_RESPONSE enabled")
        kwargs["mock_response"] = mock_answer(settings.MOCK_RESPONSE_CHARS)

    # Request token usage reporting (except for Aya which doesn't support it)
    if "c4ai-aya-expanse-32b" not in endpoint.model:
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
        response = cast(
            litellm.CustomStreamWrapper, await litellm.acompletion(**kwargs)
        )
    except litellm.ContextWindowExceededError as e:
        logger.error(
            f"context_window_exceeded: {endpoint.model}: {e}",
            extra={"request": request},
        )
        raise ContextTooLongError from e

    # OpenRouter specific params could be added here
    # transforms = [""], route= ""

    # Process streaming chunks from the API
    # Closing the stream frees the provider connection, whether the answer
    # ended, stopped early, or the visitor left and the task was cancelled.
    try:
        async for chunk in response:
            if not msg.responded_at:
                # Store first chunk ts for latency computation
                msg.responded_at = datetime.now()
            # Extract generation ID for tracking/debugging
            if not msg.generation_id and chunk.id:
                msg.generation_id = chunk.id
                logger.debug(
                    f"Response stream started for '{endpoint.model}' with generation_id='{chunk.id}'",
                    extra={"request": request},
                )
            # Extract token count from streaming completion (if available)
            if hasattr(chunk, "usage") and hasattr(chunk.usage, "completion_tokens"):
                msg.tokens = chunk.usage.completion_tokens
                logger.debug(
                    f"reported output tokens for api {endpoint.base_url} and model {endpoint.model}: {msg.tokens}",
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
    finally:
        await response.aclose()

    # Store last update ts for duration computation
    msg.updated_at = datetime.now()

    logger.debug(
        f"Response stream ended for '{endpoint.model}' with generation_id='{chunk.id}'",
        extra={"request": request},
    )

    # Final yield after loop completes
    yield msg
