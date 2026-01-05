"""
Server-Sent Events (SSE) streaming support for arena conversations.

Handles real-time streaming of model responses to the frontend using SSE protocol.
"""

import json
import logging
from typing import Any, AsyncIterator, Literal

from fastapi.responses import StreamingResponse

logger = logging.getLogger("languia")


async def stream_bot_response(
    position: Literal["a", "b"], conv_state: dict, request: Any
) -> AsyncIterator[str]:
    """
    Stream a single bot response using Server-Sent Events format.

    Args:
        position: Which model position ("a" or "b")
        conv_state: Conversation state dict with messages and model info
        request: FastAPI Request object for logging

    Yields:
        str: SSE-formatted messages (data: {...}\n\n)

    SSE Format:
        data: {"type": "chunk", "messages": [...]}

        data: {"type": "done"}

        data: {"type": "error", "error": "error message"}
    """
    from backend.arena.conversation import bot_response_async
    from backend.arena.utils import deserialize_conversation_from_redis
    from backend.utils.user import get_ip

    try:
        # Reconstruct Conversation (Pydantic) from Redis state dict
        conv = deserialize_conversation_from_redis(conv_state)

        # Get IP from request for logging
        ip = get_ip(request)

        # Stream responses from bot_response_async generator
        async for updated_state in bot_response_async(position, conv, ip):
            # Serialize Pydantic messages to dicts for JSON response
            messages = []
            for msg in updated_state.messages:
                msg_dict = msg.model_dump()
                # For assistant messages, serialize metadata properly
                if hasattr(msg, "metadata") and msg.metadata:
                    if hasattr(msg.metadata, "model_dump"):
                        msg_dict["metadata"] = msg.metadata.model_dump()
                messages.append(msg_dict)

            chunk = {"type": "chunk", "messages": messages}
            yield f"data: {json.dumps(chunk)}\n\n"

        # Signal completion
        yield f'data: {{"type": "done"}}\n\n'

    except Exception as e:
        logger.error(f"[STREAMING] Error in stream_bot_response: {e}", exc_info=True)
        error_chunk = {"type": "error", "error": str(e)}
        yield f"data: {json.dumps(error_chunk)}\n\n"


async def stream_both_responses(
    conv_a: dict, conv_b: dict, request: Any
) -> AsyncIterator[str]:
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

        data: {"type": "done"}

        data: {"type": "error", "error": "..."}
    """
    import asyncio

    try:
        # Create async generators for both models
        gen_a = stream_bot_response("a", conv_a, request)
        gen_b = stream_bot_response("b", conv_b, request)

        # Track state from both generators
        last_a = None
        last_b = None
        done_a = False
        done_b = False

        # Consume both generators in parallel
        while not (done_a and done_b):
            # Collect pending tasks
            tasks = []

            if not done_a:
                tasks.append(asyncio.create_task(_safe_next(gen_a, "a")))
            if not done_b:
                tasks.append(asyncio.create_task(_safe_next(gen_b, "b")))

            if not tasks:
                break

            # Wait for next chunk from either model
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            # Process completed chunks
            has_update = False
            for task in done:
                result = task.result()

                if result["source"] == "a":
                    if result["done"]:
                        done_a = True
                    elif result["data"] and result["data"].get("type") == "chunk":
                        # Only update if it's a chunk event, not a "done" event
                        last_a = result["data"]
                        has_update = True
                else:  # source == "b"
                    if result["done"]:
                        done_b = True
                    elif result["data"] and result["data"].get("type") == "chunk":
                        # Only update if it's a chunk event, not a "done" event
                        last_b = result["data"]
                        has_update = True

            # Yield combined state if we have updates (but not for individual "done" events)
            if has_update and (last_a or last_b):
                combined = {
                    "type": "update",
                    "a": last_a if last_a else {"type": "waiting"},
                    "b": last_b if last_b else {"type": "waiting"},
                }
                yield f"data: {json.dumps(combined)}\n\n"

        # Signal completion
        yield f'data: {{"type": "done"}}\n\n'

    except Exception as e:
        logger.error(
            f"[STREAMING] Error in stream_both_responses: {e}", exc_info=True
        )
        error_chunk = {"type": "error", "error": str(e)}
        yield f"data: {json.dumps(error_chunk)}\n\n"


async def _safe_next(generator: AsyncIterator[str], source: str) -> dict:
    """
    Safely consume next item from an async generator.

    Args:
        generator: AsyncIterator to consume from
        source: Identifier for this generator ("a" or "b")

    Returns:
        dict with keys:
            - source: str - Generator identifier
            - done: bool - Whether generator is exhausted
            - data: str | None - Next value (if not done)
    """
    try:
        value = await generator.__anext__()
        # Parse SSE data line
        if value.startswith("data: "):
            data_str = value[6:].strip()
            if data_str:
                data = json.loads(data_str)
                return {"source": source, "done": False, "data": data}

        return {"source": source, "done": False, "data": None}

    except StopAsyncIteration:
        return {"source": source, "done": True, "data": None}
    except Exception as e:
        logger.error(f"[STREAMING] Error in _safe_next for {source}: {e}")
        return {
            "source": source,
            "done": True,
            "data": {"type": "error", "error": str(e)},
        }


def create_sse_response(generator: AsyncIterator[str]) -> StreamingResponse:
    """
    Create a FastAPI StreamingResponse configured for Server-Sent Events.

    Args:
        generator: AsyncIterator yielding SSE-formatted strings

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
