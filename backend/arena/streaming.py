"""
Server-Sent Events (SSE) streaming support for arena conversations.

Handles real-time streaming of model responses to the frontend using SSE protocol.
"""

import json
import logging
import traceback
from typing import Any, AsyncGenerator, Literal, TypedDict

import litellm
import sentry_sdk
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from backend.arena.models import BOT_POS, BotPos, ErrorDetails
from backend.arena.services import update_comparison_error, update_comparison_llm_id
from backend.config import CustomModelsSelection, SelectionMode, settings
from backend.errors import ChatError
from backend.llms.data import get_llms_data, pick_replacement_model
from backend.llms.models import LLMDataEnabled
from utils.database.models import (
    AnyMessageRead,
    ComparisonRead,
    LLMMessageCreate,
    TurnRead,
)

logger = logging.getLogger("languia")


def format_sse_event(data: Any) -> str:
    """
    Format event for sse streaming with fastapi json encoder.
    """
    return f"data: {json.dumps(jsonable_encoder(data))}\n\n"


class SSEEventInit(TypedDict):
    type: Literal["init"]
    pos: BotPos
    session_hash: str


class SSEEventComplete(TypedDict):
    type: Literal["complete"]
    pos: BotPos


class SSEEventChunk(TypedDict):
    type: Literal["chunk"]
    pos: BotPos
    messages: list[AnyMessageRead | LLMMessageCreate]


class SSEEventError(TypedDict):
    type: Literal["error"]
    pos: BotPos
    error: str


AnySSEEvent = SSEEventInit | SSEEventChunk | SSEEventComplete | SSEEventError


async def stream_conversation_messages(
    pos: BotPos,
    llm: LLMDataEnabled,
    turn: TurnRead,
    turn_index: int,
    messages: list[AnyMessageRead],
    request: Request | None = None,
) -> AsyncGenerator[AnySSEEvent]:
    """
    Stream a single bot response using Server-Sent Events format.

    Args:
        pos: Which model position ("a" or "b")
        llm: LLM data
        turn: Current Turn
        turn_index: Current Turn index
        messages: List of messages to be serialized for llm call
        request: FastAPI Request object for logging

    Yields:
        str: SSE-formatted messages (data: {...}\n\n)

    SSE Format:
        data: {"type": "chunk", "messages": [...]}

        data: {"type": "complete"}

        data: {"type": "error", "error": "error message"}
    """
    from backend.arena.conversation import bot_response_async

    try:
        # Stream responses from bot_response_async generator
        async for llm_msg in bot_response_async(
            pos, llm, turn, turn_index, messages, request
        ):
            yield {"type": "chunk", "pos": pos, "messages": messages + [llm_msg]}

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


async def stream_comparison_messages(
    comparison: ComparisonRead,
    turn: TurnRead,
    request: Any | None = None,
) -> AsyncGenerator[str]:
    """
    Stream both model responses in parallel using Server-Sent Events.

    This function orchestrates streaming from both models simultaneously,
    yielding updates as they arrive from either model.

    Args:
        conv_a: First conversation state dict
        conv_b: Second conversation state dict
        request: FastAPI Request object for logging

    Yields:
        str: SSE-formatted messages with updates from both models

    SSE Event Format:
        data: {"type": "update", "a": {...}, "b": {...}}

        data: {"type": "complete"}

        data: {"type": "error", "error": "..."}
    """
    import asyncio

    turn_index = len(comparison.turns) - 1
    llms_data = get_llms_data(comparison.country_portal).enabled

    try:
        # Create async generators for both models
        generators: dict[BotPos, AsyncGenerator[AnySSEEvent]] = {
            pos: stream_conversation_messages(
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
                            generators[e.pos] = stream_conversation_messages(
                                e.pos,
                                llms_data[new_llm_id],
                                turn,
                                turn_index,
                                _get_messages(comparison, e.pos),
                                request,
                            )
                            retried[e.pos] = True
                            yield format_sse_event({"type": "swap", "pos": e.pos})
                            continue
                        # No replacement available, fall through to raise
                    raise

                for pos in BOT_POS:
                    if event["type"] == "complete":
                        complete[event["pos"]] = True

                yield format_sse_event(event)

        # Signal completion
        yield format_sse_event({"type": "complete"})
    except ChatError as e:
        # Specific chat error
        # Error logging is done in `stream_conversation_messages()`
        await update_comparison_error(
            comparison,
            ErrorDetails(message=e.message, pos=e.pos, is_timeout=e.is_timeout),
        )

        yield format_sse_event({"type": "error", "error": e.message, "pos": e.pos})
    except Exception as e:
        # General error
        if settings.SENTRY_DSN:
            # Error is silenced to be sent thru sse message, send it to sentry manually
            sentry_sdk.capture_exception(e)

        await update_comparison_error(comparison, ErrorDetails(message=str(e)))
        logger.error(
            f"[STREAMING] Error in stream_comparison_messages: {e}", exc_info=True
        )
        yield format_sse_event({"type": "error", "error": str(e)})


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
    """Check if a model was explicitly chosen by the user (custom mode)."""
    if mode != "custom" or not custom_selection:
        return False
    return model_name in custom_selection


def create_sse_response(generator: AsyncGenerator[str]) -> StreamingResponse:
    """
    Create a FastAPI StreamingResponse configured for Server-Sent Events.

    Args:
        generator: AsyncGenerator yielding SSE-formatted strings

    Returns:
        StreamingResponse configured with proper SSE headers
    """
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering for Nginx
        },
    )
