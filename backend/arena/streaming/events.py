"""
Streaming related types and utilities.
"""

import json
from typing import TYPE_CHECKING, AsyncGenerator, Literal, TypedDict

from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

if TYPE_CHECKING:
    from utils.database.models import (
        BotPos,
        ComparisonPublic,
        LLMMessageCreate,
        TurnPublic,
    )


class SSEEventMsgChunk(TypedDict):
    type: Literal["chunk"]
    pos: "BotPos"
    llm_msg: "LLMMessageCreate"


class SSEEventMsgComplete(TypedDict):
    type: Literal["complete"]
    pos: "BotPos"


class SSEEventMsgError(TypedDict):
    type: Literal["error"]
    pos: "BotPos"
    error: str


class SSEEventInit(TypedDict):
    type: Literal["init"]
    comparison: "ComparisonPublic"


class SSEEventSwap(TypedDict):
    type: Literal["swap"]
    pos: "BotPos"


class SSEEventTurn(TypedDict):
    type: Literal["add", "update"]
    turn: "TurnPublic"


class SSEEventComplete(TypedDict):
    type: Literal["complete"]


class SSEEventError(TypedDict):
    type: Literal["error"]
    error: str


AnySSEEventMsg = SSEEventMsgChunk | SSEEventMsgComplete | SSEEventMsgError
AnySSEEvent = (
    AnySSEEventMsg
    | SSEEventInit
    | SSEEventTurn
    | SSEEventSwap
    | SSEEventComplete
    | SSEEventError
)


def format_sse_event(data: AnySSEEvent) -> str:
    """
    Format event for sse streaming with fastapi json encoder.
    """
    return f"data: {json.dumps(jsonable_encoder(data))}\n\n"


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
