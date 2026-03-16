"""
Module for handling conversations with AI models.

This module manages the interaction with multiple AI models through LiteLLM,
handling streaming responses, token counting, and message tracking.

Uses Pydantic Conversation model update and validation during streaming.
"""

import asyncio
import logging
import time
from typing import AsyncGenerator

from fastapi import Request
from litellm.litellm_core_utils.token_counter import token_counter

from backend.arena.cache import (
    CachedResponse,
    get_cached_response,
    store_cached_response,
)
from backend.arena.litellm import litellm_stream_iter
from backend.arena.models import (
    AnyMessage,
    AssistantMessage,
    AssistantMessageMetadata,
    BotPos,
    Conversation,
    SystemMessage,
)
from backend.errors import EmptyResponseError

logger = logging.getLogger("languia")


def _is_first_turn(state: Conversation) -> bool:
    """Check if this is the first turn (no assistant messages yet)."""
    return not any(isinstance(m, AssistantMessage) for m in state.messages)


def _get_user_prompt(state: Conversation) -> str:
    """Get the first user message content for cache key."""
    for msg in state.messages:
        if not isinstance(msg, SystemMessage):
            return msg.content
    return ""


async def _stream_cached_response(
    position: BotPos,
    state: Conversation,
    cached: CachedResponse,
) -> AsyncGenerator[list[AnyMessage]]:
    """
    Simulate streaming from a cached response.

    Chunks the cached content and yields with small delays to mimic
    real streaming behavior for consistent UX.
    """
    metadata = AssistantMessageMetadata(
        generation_id="cached",
        bot=position,
        output_tokens=cached["output_tokens"],
        is_cached=True,
    )
    current_msg = AssistantMessage(metadata=metadata)
    state.messages.append(current_msg)

    start_tstamp = time.time()

    content = cached["content"]
    reasoning = cached["reasoning"].strip()

    if reasoning:
        current_msg.reasoning = reasoning

    # Simulate streaming: emit content in chunks
    chunk_size = max(20, len(content) // 15)  # ~15 chunks
    emitted = 0
    while emitted < len(content):
        end = min(emitted + chunk_size, len(content))
        current_msg.content = content[:end].strip()
        if current_msg.content or current_msg.reasoning:
            yield state.messages
        emitted = end

        try:
            await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            logger.exception("CANCELLED")
            # Sleep can be cancelled and raise StopAsyncGenerator error
            # Simply silence error
            pass

    # Final yield with complete content and timing
    current_msg.content = content.strip()
    current_msg.metadata.duration = time.time() - start_tstamp
    yield state.messages


async def bot_response_async(
    position: BotPos,
    state: Conversation,
    request: Request,
    temperature=0.7,
    max_new_tokens=16384,
) -> AsyncGenerator[list[AnyMessage]]:
    """
    Stream a response from an AI model asynchronously.

    This is an async generator function that yields conversation state updates as the model
    generates responses token by token.

    Args:
        position: Which model position ("a" or "b") to respond
        state: Conversation (Pydantic model) with messages and model info
        request: FastAPI request for logging
        temperature: Sampling temperature (default 0.7)
        max_new_tokens: Maximum tokens to generate (default 4096)

    Yields:
        Updated message list as response chunks arrive

    Raises:
        EmptyResponseError: If model returns empty response
    """
    is_first_turn = _is_first_turn(state)

    # Try cache on first turn only
    if is_first_turn:
        prompt = _get_user_prompt(state)
        cached = get_cached_response(state.model_name, prompt)
        if cached:
            logger.info(
                f"[CACHE] Serving cached response for {state.model_name}",
                extra={"request": request},
            )
            async for messages in _stream_cached_response(position, state, cached):
                yield messages
            return

    # Add new partial AssistantMessage to chat
    metadata = AssistantMessageMetadata(generation_id="", bot=position)
    current_msg = AssistantMessage(metadata=metadata)
    state.messages.append(current_msg)

    # Track generation start time for performance metrics
    start_tstamp = time.time()

    # Initialize streaming iterator from LiteLLM
    stream_iter = litellm_stream_iter(
        model_name=state.model_name,
        endpoint=state.llm.endpoint,
        messages=state.messages,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        request=request,
    )

    # Process streaming response chunks and update current message
    for data in stream_iter:
        if not current_msg.metadata.generation_id:
            current_msg.metadata.generation_id = data["generation_id"]
        if data["output_tokens"]:
            current_msg.metadata.output_tokens = data["output_tokens"]

        if data["content"] or data["reasoning"]:
            current_msg.content = data["content"].strip()
            current_msg.reasoning = data["reasoning"].strip()

        # Yield complete chat only if there's content to display in current message
        if current_msg.content or current_msg.reasoning:
            yield state.messages

    # Calculate total generation duration
    stop_tstamp = time.time()
    current_msg.metadata.duration = stop_tstamp - start_tstamp
    logger.debug(
        f"duration for {data["generation_id"]}: {current_msg.metadata.duration}",
        extra={"request": request},
    )

    # Check for empty responses and raise error (check on data that is not stripped)
    if not data["content"] and not data["reasoning"]:
        logger.error(
            f"reponse_vide: {state.model_name}, message: {current_msg}",
            exc_info=True,
            extra={"request": request},
        )
        raise EmptyResponseError(
            f"No answer from API '{state.llm.endpoint.api_model_id}' for model '{state.model_name}'"
        )

    # Fallback: count tokens locally if API didn't provide them
    if not current_msg.metadata.output_tokens:
        current_msg.metadata.output_tokens = token_counter(
            text=[data["reasoning"], data["content"]],
            model=state.model_name,
        )

    # Final update with complete response and timing data
    yield state.messages

    # Store successful response in cache (first turn only)
    if is_first_turn:
        store_cached_response(
            state.model_name,
            _get_user_prompt(state),
            CachedResponse(
                content=current_msg.content,
                reasoning=current_msg.reasoning,
                output_tokens=current_msg.metadata.output_tokens,
            ),
        )
