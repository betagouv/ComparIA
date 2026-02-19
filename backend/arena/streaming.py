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

from backend.arena.models import (
    BOT_POS,
    AnyMessage,
    BotPos,
    Conversation,
    Conversations,
    ErrorDetails,
    UserMessage,
    create_conversation,
)
from backend.config import CustomModelsSelection, SelectionMode, settings
from backend.errors import ChatError
from backend.llms.data import get_llms_data

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
    messages: list[AnyMessage]


class SSEEventError(TypedDict):
    type: Literal["error"]
    pos: BotPos
    error: str


AnySSEEvent = SSEEventInit | SSEEventChunk | SSEEventComplete | SSEEventError


async def stream_conversation_messages(
    pos: BotPos, conv: Conversation, request: Request
) -> AsyncGenerator[AnySSEEvent]:
    """
    Stream a single bot response using Server-Sent Events format.

    Args:
        pos: Which model position ("a" or "b")
        conv_state: Conversation state dict with messages and model info
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
        async for messages in bot_response_async(pos, conv, request):
            yield {"type": "chunk", "pos": pos, "messages": messages}

        yield {"type": "complete", "pos": pos}

        logger.info(
            f"response_modele_{pos} ({conv.model_name}): {str(conv.messages[-1].content)}",
            extra={"request": request},
        )

    except Exception as e:
        error_message = str(e)

        if settings.SENTRY_DSN:
            # Error is silenced to be sent thru sse message, send it to sentry manually
            # TODO: only capture model name to sort more easily in sentry
            sentry_sdk.capture_exception(e)

        error_reason = f"error_during_convo: {conv.model_name}, {conv.llm.endpoint.api_type}, {error_message}"

        # TODO ContextLengthError: do not log to controller?
        try:
            import requests

            requests.post(
                f"{settings.LANGUIA_CONTROLLER_URL}/models/{conv.model_name}/error",
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

        raise ChatError(message=error_message, pos=pos, is_timeout=isinstance(e, litellm.Timeout))


async def stream_comparison_messages(
    conversations: Conversations, request: Any
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

    try:
        # Create async generators for both models
        generators: dict[BotPos, AsyncGenerator[AnySSEEvent]] = {
            "a": stream_conversation_messages(
                "a", conversations.conversation_a, request
            ),
            "b": stream_conversation_messages(
                "b", conversations.conversation_b, request
            ),
        }
        # Track state from both generators
        complete: dict[BotPos, bool] = {"a": False, "b": False}
        # Track timeout swap attempts (max one per position)
        retried: dict[BotPos, bool] = {"a": False, "b": False}
        is_first_turn = conversations.conv_turns == 0

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

            # Process completed chunks
            for task in completed:
                try:
                    event = task.result()
                except ChatError as e:
                    # On first-turn timeout, swap the model if it wasn't user-selected
                    if (
                        e.is_timeout
                        and is_first_turn
                        and not retried[e.pos]
                        and not _is_model_user_selected(
                            getattr(
                                conversations, f"conversation_{e.pos}"
                            ).model_name,
                            conversations.mode,
                            conversations.custom_models_selection,
                        )
                    ):
                        new_model = _pick_replacement_model(conversations, e.pos)
                        if new_model:
                            old_name = getattr(
                                conversations, f"conversation_{e.pos}"
                            ).model_name
                            logger.warning(
                                f"Model '{old_name}' timed out, swapping to '{new_model}'"
                            )
                            user_msg = UserMessage(
                                content=conversations.opening_msg
                            )
                            new_conv = create_conversation(
                                new_model,
                                conversations.country_portal,
                                user_msg,
                            )
                            setattr(
                                conversations,
                                f"conversation_{e.pos}",
                                new_conv,
                            )
                            generators[e.pos] = (
                                stream_conversation_messages(
                                    e.pos, new_conv, request
                                )
                            )
                            retried[e.pos] = True
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
        conversations.error = ErrorDetails(message=e.message, pos=e.pos)
        yield format_sse_event({"type": "error", "error": e.message, "pos": e.pos})
    except Exception as e:
        # General error
        if settings.SENTRY_DSN:
            # Error is silenced to be sent thru sse message, send it to sentry manually
            sentry_sdk.capture_exception(e)

        conversations.error = ErrorDetails(message=str(e))
        logger.error(
            f"[STREAMING] Error in stream_comparison_messages: {e}", exc_info=True
        )
        yield format_sse_event({"type": "error", "error": str(e)})


def _is_model_user_selected(
    model_name: str, mode: SelectionMode, custom_selection: CustomModelsSelection
) -> bool:
    """Check if a model was explicitly chosen by the user (custom mode)."""
    if mode != "custom" or not custom_selection:
        return False
    return model_name in custom_selection


def _pick_replacement_model(conversations: Conversations, pos: BotPos) -> str | None:
    """Pick a replacement model from the appropriate pool, excluding both current models."""
    models = get_llms_data(conversations.country_portal)
    other_pos: BotPos = "b" if pos == "a" else "a"
    failing = getattr(conversations, f"conversation_{pos}").model_name
    other = getattr(conversations, f"conversation_{other_pos}").model_name
    excluded = [failing, other]

    # Pick from the right pool based on mode
    if conversations.mode == "small-models":
        pool = models.small_models
    elif conversations.mode == "big-vs-small":
        pool = models.big_models if failing in models.big_models else models.small_models
    else:
        pool = models.random_models

    try:
        return models.pick_one(pool, excluded=excluded)
    except Exception:
        return None


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
