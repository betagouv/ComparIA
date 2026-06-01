"""
Module for handling conversations with LLMs.

This module manages the interaction with LLMs through LiteLLM, handling events,
errors, message tracking, etc.
"""

import asyncio
import logging
import traceback
from datetime import datetime
from typing import Any, AsyncGenerator

import litellm
import sentry_sdk
from fastapi import Request
from litellm.litellm_core_utils.token_counter import token_counter

from backend.arena.cache import (
    CachedResponse,
    get_cached_response,
    store_cached_response,
)
from backend.arena.services.comparison import (
    update_comparison_error,
    update_comparison_llm_id,
)
from backend.arena.streaming.events import AnySSEEvent, AnySSEEventMsg
from backend.arena.streaming.litellm import litellm_stream_iter
from backend.config import CustomModelsSelection, SelectionMode, settings
from backend.errors import ChatError, EmptyResponseError
from backend.llms.data import get_llms_data, pick_replacement_model
from backend.llms.models import LLMDataEnabled
from utils.database.models import (
    BOT_POS,
    AnyMessageRead,
    BotPos,
    ComparisonRead,
    ErrorDetails,
    LLMMessageCreate,
    TurnRead,
)

logger = logging.getLogger("languia")


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


async def ask_llm(
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


async def stream_llm_response(
    pos: BotPos,
    llm: LLMDataEnabled,
    turn: TurnRead,
    turn_index: int,
    messages: list[AnyMessageRead],
    request: Request | None = None,
) -> AsyncGenerator[AnySSEEventMsg]:
    """
    Stream a single LLM response using Server-Sent Events format.

    Args:
        pos: Which LLM position ("a" or "b")
        llm: LLM data
        turn: Current Turn
        turn_index: Current Turn index
        messages: List of messages to be serialized for llm call
        request: FastAPI Request object for logging

    Yields:
        AnySSEEventMsg
    """

    try:
        # Stream responses from ask_llm generator
        async for llm_msg in ask_llm(pos, llm, turn, turn_index, messages, request):
            yield {"type": "chunk", "pos": pos, "llm_msg": llm_msg}

        yield {"type": "complete", "pos": pos}

        logger.info(
            f"response_modele_{pos} ({llm.id}): {llm_msg.content}",
            extra={"request": request},
        )

    except Exception as e:
        error_message = str(e)

        if settings.SENTRY_DSN:
            # Error is silenced to be sent thru sse message, send it to sentry manually
            # TODO: only capture model name to sort more easily in sentry
            sentry_sdk.capture_exception(e)

        error_reason = (
            f"error_during_convo: {llm.id}, {llm.endpoint.api_type}, {error_message}"
        )

        # TODO ContextLengthError: do not log to controller?
        try:
            import requests

            requests.post(
                f"{settings.LANGUIA_CONTROLLER_URL}/models/{llm.id}/error",
                json={"error": error_reason},
                timeout=1,
            )
        except:
            pass

        logger.exception(
            error_reason,
            extra={
                "request": request,
                "error": error_message,
                "stacktrace": traceback.format_exc(),
            },
            exc_info=True,
        )

        raise ChatError(
            message=error_message, pos=pos, is_timeout=isinstance(e, litellm.Timeout)
        )


async def ask_llms(
    comparison: ComparisonRead,
    turn: TurnRead,
    request: Any | None = None,
) -> AsyncGenerator[AnySSEEvent]:
    """
    Stream both LLMs responses in parallel using Server-Sent Events.

    This function orchestrates streaming from both LLMs simultaneously,
    yielding updates as they arrive from either model.

    Args:
        comparison: current Comparison
        turn: current Turn
        request: FastAPI Request object for logging

    Yields:
        AnySSEEvent
    """
    import asyncio

    turn_index = len(comparison.turns) - 1
    llms_data = get_llms_data().enabled

    try:
        # Create async generators for both models
        generators: dict[BotPos, AsyncGenerator[AnySSEEventMsg]] = {
            pos: stream_llm_response(
                pos,
                llms_data[getattr(comparison, f"llm_id_{pos}")],
                turn,
                turn_index,
                _get_messages(comparison, pos),
                request,
            )
            for pos in BOT_POS
        }
        # Track state from both generators
        complete: dict[BotPos, bool] = {"a": False, "b": False}
        # Track timeout swap attempts (max one per position)
        retried: dict[BotPos, bool] = {"a": False, "b": False}

        # Consume both generators in parallel
        while not (complete["a"] and complete["b"]):
            # Collect pending tasks
            tasks = [
                asyncio.create_task(anext(generators[pos]))
                for pos in BOT_POS
                if not complete[pos]
            ]

            if not tasks:
                break

            # Wait for next chunk from either model
            completed, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel pending tasks to avoid concurrent anext() on the same generator
            for task in pending:
                task.cancel()

            # Process completed chunks
            for task in completed:
                try:
                    event = task.result()
                except ChatError as e:
                    # On first-turn timeout, swap the model if it wasn't user-selected
                    failing_llm_id = getattr(comparison, f"llm_id_{e.pos}")
                    if (
                        e.is_timeout
                        and turn_index == 0
                        and not retried[e.pos]
                        and not _is_model_user_selected(
                            failing_llm_id,
                            comparison.mode,
                            comparison.custom_models_selection,
                        )
                    ):
                        if new_llm_id := pick_replacement_model(comparison, e.pos):
                            await update_comparison_llm_id(
                                comparison, e.pos, new_llm_id
                            )
                            logger.warning(
                                f"LLM '{failing_llm_id}' timed out, swapping to '{new_llm_id}'"
                            )
                            generators[e.pos] = stream_llm_response(
                                e.pos,
                                llms_data[new_llm_id],
                                turn,
                                turn_index,
                                _get_messages(comparison, e.pos),
                                request,
                            )
                            retried[e.pos] = True
                            yield {"type": "swap", "pos": e.pos}
                            continue
                        # No replacement available, fall through to raise
                    raise

                for pos in BOT_POS:
                    if event["type"] == "complete":
                        complete[event["pos"]] = True

                yield event

        # Signal completion
        yield {"type": "complete"}
    except ChatError as e:
        # Specific chat error
        # Error logging is done in `stream_llm_response()`
        await update_comparison_error(
            comparison,
            ErrorDetails(message=e.message, pos=e.pos, is_timeout=e.is_timeout),
        )

        yield {"type": "error", "error": e.message, "pos": e.pos}
    except Exception as e:
        # General error
        if settings.SENTRY_DSN:
            # Error is silenced to be sent thru sse message, send it to sentry manually
            sentry_sdk.capture_exception(e)

        await update_comparison_error(comparison, ErrorDetails(message=str(e)))
        logger.error(f"[STREAMING] Error in ask_llms: {e}", exc_info=True)
        yield {"type": "error", "error": str(e)}


def _get_messages(comparison: ComparisonRead, pos: BotPos) -> list[AnyMessageRead]:
    messages: list[AnyMessageRead] = []

    if system_msg := getattr(comparison, f"system_msg_{pos}"):
        messages.append(system_msg)

    for turn in comparison.turns:
        messages.append(turn.user_msg)
        if llm_msg := getattr(turn, f"llm_msg_{pos}"):
            messages.append(llm_msg)

    return messages


def _is_model_user_selected(
    model_name: str, mode: SelectionMode, custom_selection: CustomModelsSelection
) -> bool:
    """
    Check if a model was explicitly chosen by the user (custom mode).
    """
    if mode != "custom" or not custom_selection:
        return False
    return model_name in custom_selection
