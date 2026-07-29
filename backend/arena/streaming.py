"""
Server-Sent Events (SSE) streaming support for arena comparisons.

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

from backend.arena.tools import ToolSpec, resolve_tools
from backend.arena.conversation import (
    AnyMessageRead,
    SystemMessageRead,
    bot_response_async,
)
from backend.arena.services import update_comparison_error, update_comparison_llm_id
from backend.config import CustomModelsSelection, SelectionMode, settings
from backend.errors import ChatError
from backend.llms.data import get_llms_data, pick_replacement_model
from backend.llms.models import LLMDataEnabled
from utils.database.models import (
    BOT_POS,
    BotPos,
    ComparisonPublic,
    ComparisonRead,
    ErrorDetails,
    LLMMessageCreate,
    TurnPublic,
    TurnRead,
)

logger = logging.getLogger("languia")


class SSEEventMsgChunk(TypedDict):
    type: Literal["chunk"]
    pos: BotPos
    llm_msg: LLMMessageCreate


class SSEEventMsgComplete(TypedDict):
    type: Literal["complete"]
    pos: BotPos


class SSEEventMsgError(TypedDict):
    type: Literal["error"]
    pos: BotPos
    error: str


class SSEEventInit(TypedDict):
    type: Literal["init"]
    comparison: ComparisonPublic


class SSEEventSwap(TypedDict):
    type: Literal["swap"]
    pos: BotPos


class SSEEventTurn(TypedDict):
    type: Literal["add", "update"]
    turn: TurnPublic


class SSEEventComplete(TypedDict):
    type: Literal["complete"]


class SSEEventError(TypedDict):
    type: Literal["error"]
    error: str


class SSEEventWarning(TypedDict):
    """Only event of the stream when a check asks the user to confirm."""

    type: Literal["warning"]
    warnings: list[dict[str, str]]
    warning_token: str


AnySSEEventMsg = SSEEventMsgChunk | SSEEventMsgComplete | SSEEventMsgError
AnySSEEvent = (
    AnySSEEventMsg
    | SSEEventInit
    | SSEEventTurn
    | SSEEventSwap
    | SSEEventComplete
    | SSEEventError
    | SSEEventWarning
)


def format_sse_event(data: AnySSEEvent) -> str:
    """
    Format event for sse streaming with fastapi json encoder.
    """
    return f"data: {json.dumps(jsonable_encoder(data))}\n\n"


async def stream_llm_response(
    pos: BotPos,
    llm: LLMDataEnabled,
    turn: TurnRead,
    turn_index: int,
    messages: list[AnyMessageRead],
    request: Request | None = None,
    tools: list[ToolSpec] | None = None,
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
        # Stream responses from bot_response_async generator
        async for llm_msg in bot_response_async(
            pos,
            llm,
            turn,
            turn_index,
            messages,
            request,
            tools=tools,
        ):
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


async def stream_comparison_messages(
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
    llms_data = (await get_llms_data()).enabled
    # Resolved once for the turn: both models are offered exactly the same set,
    # and a configured tool is looked up once rather than once per model.
    tools = await resolve_tools(["web_search"] if comparison.web_search_enabled else [])

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
                tools,
            )
            for pos in BOT_POS
        }
        # Track state from both generators
        complete: dict[BotPos, bool] = {"a": False, "b": False}
        # Track timeout swap attempts (max one per position)
        retried: dict[BotPos, bool] = {"a": False, "b": False}
        pending_by_pos: dict[BotPos, asyncio.Task[AnySSEEventMsg]] = {
            pos: asyncio.create_task(anext(generator))
            for pos, generator in generators.items()
        }

        # Consume both generators in parallel
        while not (complete["a"] and complete["b"]):
            if not pending_by_pos:
                break

            # Wait for next chunk from either model
            completed_tasks, _ = await asyncio.wait(
                pending_by_pos.values(), return_when=asyncio.FIRST_COMPLETED
            )

            # Process completed chunks
            for task in completed_tasks:
                pos = next(
                    candidate_pos
                    for candidate_pos, candidate_task in pending_by_pos.items()
                    if candidate_task is task
                )
                del pending_by_pos[pos]
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
                        if new_llm_id := await pick_replacement_model(
                            comparison, e.pos
                        ):
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
                                tools,
                            )
                            pending_by_pos[e.pos] = asyncio.create_task(
                                anext(generators[e.pos])
                            )
                            retried[e.pos] = True
                            yield {"type": "swap", "pos": e.pos}
                            continue
                        # No replacement available, fall through to raise
                    raise

                if event["type"] == "complete":
                    complete[event["pos"]] = True
                else:
                    pending_by_pos[pos] = asyncio.create_task(anext(generators[pos]))

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
        logger.error(
            f"[STREAMING] Error in stream_comparison_messages: {e}", exc_info=True
        )
        yield {"type": "error", "error": str(e)}
    finally:
        remaining_tasks = list(locals().get("pending_by_pos", {}).values())
        for task in remaining_tasks:
            task.cancel()
        if remaining_tasks:
            await asyncio.gather(*remaining_tasks, return_exceptions=True)


def _get_messages(comparison: ComparisonRead, pos: BotPos) -> list[AnyMessageRead]:
    messages: list[AnyMessageRead] = []

    if system_msg := getattr(comparison, f"system_msg_{pos}"):
        messages.append(SystemMessageRead(content=system_msg))

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
    return str(model_name) in custom_selection


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
