"""
Server-Sent Events (SSE) streaming support for arena conversations.

Handles real-time streaming of model responses to the frontend using SSE protocol.
"""

import json
import logging
import traceback
from typing import Any, AsyncGenerator, Literal, TypedDict

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
)
from backend.config import settings
from backend.errors import ChatError

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
    from backend.utils.user import get_ip

    try:
        # Get IP from request for logging
        ip = get_ip(request)

        # Stream responses from bot_response_async generator
        async for messages in bot_response_async(pos, conv, ip):
            # Serialize Pydantic messages to dicts for JSON response

            yield {"type": "chunk", "pos": pos, "messages": messages}

        yield {"type": "complete", "pos": pos}

        logger.info(
            f"response_modele_{pos} ({conv.model_name}): {str(conv.messages[-1].content)}",
            extra={"request": request},
        )

    except Exception as e:
        error_message = str(e)

        if settings.SENTRY_DSN:
            # TODO: only capture model name to sort more easily in sentry
            sentry_sdk.capture_exception(e)

        error_reason = f"error_during_convo: {conv.model_name}, {conv.llm.endpoint.api_type}, {error_message}"

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

        raise ChatError(message=error_message, pos=pos)


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
                event = task.result()

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
        # FIXME log to controller?
        conversations.error = ErrorDetails(message=str(e))
        logger.error(
            f"[STREAMING] Error in stream_comparison_messages: {e}", exc_info=True
        )
        yield format_sse_event({"type": "error", "error": str(e)})


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
