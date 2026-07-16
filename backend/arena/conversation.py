"""
Module for handling conversations with LLMs.

This module manages the interaction with LLMs through LiteLLM,
handling streaming responses, token counting, and message tracking.
"""

import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator, Literal

from fastapi import Request
from litellm.litellm_core_utils.token_counter import token_counter
from pydantic import BaseModel

from backend.arena.cache import (
    CachedResponse,
    get_cached_response,
    store_cached_response,
)
from backend.arena.litellm import litellm_stream_iter
from backend.errors import EmptyResponseError
from backend.llms.models import LLMDataEnabled
from utils.database.models import (
    BotPos,
    LLMMessageCreate,
    LLMMessageRead,
    TurnRead,
    UserMessageRead,
)

logger = logging.getLogger("languia")


class SystemMessageRead(BaseModel):
    role: Literal["system"] = "system"
    content: str


AnyMessageRead = LLMMessageRead | SystemMessageRead | UserMessageRead


async def _stream_cached_response(
    pos: BotPos,
    turn: TurnRead,
    cached: CachedResponse,
) -> AsyncGenerator[LLMMessageCreate]:
    """
    Simulate streaming from a cached response.

    Chunks the cached content and yields with small delays to mimic
    real streaming behavior for consistent UX.
    """
    llm_msg = LLMMessageCreate(
        created_at=datetime.now(),
        responded_at=datetime.now(),
        reasoning_content=cached["reasoning"].strip(),
        generation_id="cached",
        tokens=cached["output_tokens"],
        is_cached=True,
    )
    setattr(turn, f"llm_msg_{pos}", llm_msg)

    # Simulate streaming: emit content in chunks
    content_len = len(cached["content"])
    chunk_size = max(20, content_len // 15)  # ~15 chunks
    emitted = 0
    while emitted < content_len:
        emitted = min(emitted + chunk_size, content_len)
        llm_msg.content = cached["content"][:emitted].strip()
        if llm_msg.content or llm_msg.reasoning_content:
            yield llm_msg

        try:
            await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            # Sleep can be cancelled and raise StopAsyncGenerator error
            # Simply silence error
            pass

    # Final yield with complete content and timing
    llm_msg.content = cached["content"].strip()
    llm_msg.updated_at = datetime.now()

    yield llm_msg


async def bot_response_async(
    pos: BotPos,
    llm: LLMDataEnabled,
    turn: TurnRead,
    turn_index: int,
    messages: list[AnyMessageRead],
    request: Request | None = None,
    temperature=0.7,
    max_new_tokens=16384,
) -> AsyncGenerator[LLMMessageCreate]:
    """
    Stream a response from a LLM asynchronously.

    This is an async generator function that yields LLMMessage updates as the
    LLM generates the response token by token.

    Args:
        pos: Which LLM position ("a" or "b") to respond
        llm: LLM data
        turn: Current Turn
        turn_index: Current Turn index
        messages: List of messages to be serialized for llm call
        request: FastAPI request for logging
        temperature: Sampling temperature (default 0.7)
        max_new_tokens: Maximum tokens to generate (default 4096)

    Yields:
        Updated LLMMessageCreate as response chunks arrive

    Raises:
        EmptyResponseError: If the LLM returns empty response
    """
    # Try cache on first turn only
    if turn_index == 0:
        cached = get_cached_response(llm.id, turn.user_msg.content)
        if cached:
            logger.info(
                f"[CACHE] Serving cached response for {llm.id}",
                extra={"request": request},
            )
            async for llm_msg in _stream_cached_response(pos, turn, cached):
                yield llm_msg
            return

    # Add new partial LLMMessage to Turn (for accumulating streamed response)
    llm_msg = LLMMessageCreate()
    setattr(turn, f"llm_msg_{pos}", llm_msg)

    # Initialize streaming iterator from LiteLLM
    # Use message to avoid sending the empty AssistantMessage placeholder
    # (some providers like Cohere reject messages with empty content)
    stream_iter = litellm_stream_iter(
        llm=llm,
        messages=messages,
        msg=llm_msg,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        request=request,
    )

    # Process streaming response chunks and update current message
    for llm_msg in stream_iter:
        # Yield complete chat only if there's content to display in current message
        if llm_msg.content or llm_msg.reasoning_content:
            yield llm_msg

    duration = (llm_msg.updated_at - llm_msg.created_at).total_seconds()
    logger.debug(
        f"duration for {llm_msg.generation_id}: {duration}", extra={"request": request}
    )
    # Check for empty responses and raise error (check on data that is not stripped)
    if not llm_msg.content and not llm_msg.reasoning_content:
        logger.error(
            f"reponse_vide: {llm.id}, message: {llm_msg}",
            exc_info=True,
            extra={"request": request},
        )
        raise EmptyResponseError(
            f"No answer from API '{llm.endpoint.api_model_id}' for model '{llm.id}'"
        )

    # Fallback: count tokens locally if API didn't provide them
    if not llm_msg.tokens:
        llm_msg.tokens = token_counter(
            text=[llm_msg.reasoning_content, llm_msg.content],
            model=llm.id,
        )

    # Final update with complete response and timing data
    yield llm_msg

    # Store successful response in cache (first turn only)
    if turn_index == 0:
        store_cached_response(
            llm.id,
            turn.user_msg.content,
            CachedResponse(
                content=llm_msg.content,
                reasoning=llm_msg.reasoning_content,
                output_tokens=llm_msg.tokens,
            ),
        )
