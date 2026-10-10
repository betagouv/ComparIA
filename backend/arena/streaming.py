"""
Server-Sent Events (SSE) streaming support for arena comparisons.

Handles real-time streaming of model responses to the frontend using SSE protocol.
"""

import asyncio
import inspect
import json
import logging
import traceback
from typing import Any, AsyncGenerator, Awaitable, Callable, Literal, TypedDict

import litellm
import sentry_sdk
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from backend.arena.conversation import (
    AnyMessageRead,
    SystemMessageRead,
    bot_response_async,
)
from backend.arena.services import update_comparison_error, update_comparison_llm_id
from backend.config import CustomModelsSelection, SelectionMode, settings
from backend.errors import ChatError, ContextTooLongError, EmptyResponseError
from backend.llms.data import get_llms_data, pick_replacement_model
from backend.llms.models import LLMDataEnabled
from utils.database.models import (
    BOT_POS,
    BotPos,
    ComparisonPublic,
    ComparisonRead,
    ErrorCode,
    ErrorDetails,
    LLMMessageCreate,
    TurnPublic,
    TurnRead,
)

logger = logging.getLogger("languia")


def error_code(e: Exception) -> ErrorCode:
    """The one thing about a failure the browser is allowed to be told.

    Provider messages carry base URLs, provider names and model identity, so
    sending them on would tell a voter who they are voting for. `ChatError`
    carries the code in its `message`, which is what reaches the client.
    """
    if isinstance(e, litellm.Timeout):
        return "timeout"
    if isinstance(e, ContextTooLongError):
        return "context_too_long"
    if isinstance(e, EmptyResponseError):
        return "empty_response"
    return "provider_error"


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
    error: ErrorCode


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
    error: ErrorCode


class SSEEventWarning(TypedDict):
    """Only event of the stream when a check asks the user to confirm."""

    type: Literal["warning"]
    warnings: list[dict[str, str]]
    warning_token: str


class SSEEventInterrupted(TypedDict):
    """Last event of a stream the user stopped: the turn with its partial answers."""

    type: Literal["interrupted"]
    turn: TurnPublic


AnySSEEventMsg = SSEEventMsgChunk | SSEEventMsgComplete | SSEEventMsgError
AnySSEEvent = (
    AnySSEEventMsg
    | SSEEventInit
    | SSEEventTurn
    | SSEEventSwap
    | SSEEventComplete
    | SSEEventError
    | SSEEventWarning
    | SSEEventInterrupted
)

StopRequested = Callable[[], bool] | Callable[[], Awaitable[bool]]
# How often at most the stop flag is read while chunks keep coming.
STOP_POLL_INTERVAL = 0.5


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
            pos, llm, turn, turn_index, messages, request
        ):
            yield {"type": "chunk", "pos": pos, "llm_msg": llm_msg}

        yield {"type": "complete", "pos": pos}

        # The answer itself is kept out: it is quoted back from the prompt often
        # enough to carry whatever the user put in it.
        logger.info(
            f"response_modele_{pos} ({llm.id}): {len(llm_msg.content or '')} chars",
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

        logger.exception(
            error_reason,
            extra={
                "request": request,
                "error": error_message,
                "stacktrace": traceback.format_exc(),
            },
            exc_info=True,
        )

        # The raw message stops here, in the log and in Sentry above.
        raise ChatError(
            message=error_code(e), pos=pos, is_timeout=isinstance(e, litellm.Timeout)
        )


async def stream_comparison_messages(
    comparison: ComparisonRead,
    turn: TurnRead,
    request: Any | None = None,
    stop_requested: StopRequested | None = None,
) -> AsyncGenerator[AnySSEEvent]:
    """
    Stream both LLMs responses in parallel using Server-Sent Events.

    This function orchestrates streaming from both LLMs simultaneously,
    yielding updates as they arrive from either model.

    Args:
        comparison: current Comparison
        turn: current Turn
        request: FastAPI Request object for logging
        stop_requested: polled between chunks; when it answers True both
            provider streams are closed, the sides still running are flagged
            interrupted, and an 'interrupted' event ends the stream.

    Yields:
        AnySSEEvent
    """

    turn_index = len(comparison.turns) - 1
    llms_data = (await get_llms_data()).enabled

    generators: dict[BotPos, AsyncGenerator[AnySSEEventMsg]] = {}
    # One live task per side. A task is only re-armed once it has completed:
    # cancelling a pending anext() would throw into the generator and close
    # the provider stream.
    tasks: dict[BotPos, asyncio.Task[AnySSEEventMsg]] = {}

    try:
        # Create async generators for both models
        generators = {
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

        loop = asyncio.get_running_loop()
        last_poll = loop.time()

        # Consume both generators in parallel
        while not (complete["a"] and complete["b"]):
            for pos in BOT_POS:
                if not complete[pos] and pos not in tasks:
                    tasks[pos] = asyncio.create_task(anext(generators[pos]))

            if not tasks:
                break

            # Wait for next chunk from either model. The timeout is what lets
            # a stop land while a provider is silent.
            completed, _ = await asyncio.wait(
                tasks.values(),
                return_when=asyncio.FIRST_COMPLETED,
                timeout=STOP_POLL_INTERVAL if stop_requested else None,
            )

            if stop_requested and loop.time() - last_poll >= STOP_POLL_INTERVAL:
                last_poll = loop.time()
                if await _answers(stop_requested):
                    await _shut_down(tasks, generators)
                    for pos in BOT_POS:
                        llm_msg = getattr(turn, f"llm_msg_{pos}")
                        if not complete[pos] and llm_msg is not None:
                            llm_msg.interrupted = True
                    logger.info(
                        f"[STREAMING] Stopped comparison '{comparison.id}' on request",
                        extra={"request": request},
                    )
                    yield {
                        "type": "interrupted",
                        "turn": TurnPublic.model_validate(turn),
                    }
                    return

            # Process completed chunks
            for task in completed:
                pos = next(p for p, t in tasks.items() if t is task)
                del tasks[pos]

                try:
                    event = task.result()
                except StopAsyncIteration:
                    # A generator that ends without its 'complete' event has
                    # nothing more to say; count the side as done.
                    complete[pos] = True
                    continue
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
                            )
                            retried[e.pos] = True
                            yield {"type": "swap", "pos": e.pos}
                            continue
                        # No replacement available, fall through to raise
                    raise

                if event["type"] == "complete":
                    complete[event["pos"]] = True

                yield event

        # Signal completion
        yield {"type": "complete"}
    except ChatError as e:
        # Specific chat error
        # Error logging is done in `stream_llm_response()`
        code = e.message
        await update_comparison_error(
            comparison,
            ErrorDetails(code=code, message=code, pos=e.pos, is_timeout=e.is_timeout),
        )

        yield {"type": "error", "error": code, "pos": e.pos}
    except Exception as e:
        # General error
        if settings.SENTRY_DSN:
            # Error is silenced to be sent thru sse message, send it to sentry manually
            sentry_sdk.capture_exception(e)

        # str(e) would name the provider, so only the generic code is stored.
        await update_comparison_error(
            comparison, ErrorDetails(code="provider_error", message="provider_error")
        )
        logger.error(
            f"[STREAMING] Error in stream_comparison_messages: {e}", exc_info=True
        )
        yield {"type": "error", "error": "provider_error"}
    finally:
        await _shut_down(tasks, generators)


async def _answers(stop_requested: StopRequested) -> bool:
    result = stop_requested()
    if inspect.isawaitable(result):
        return await result
    return result


async def _shut_down(
    tasks: dict[BotPos, "asyncio.Task[AnySSEEventMsg]"],
    generators: dict[BotPos, AsyncGenerator[AnySSEEventMsg]],
) -> None:
    """Cancel whatever is still reading a provider and close both streams."""
    for task in tasks.values():
        task.cancel()
    await asyncio.gather(*tasks.values(), return_exceptions=True)
    tasks.clear()
    for generator in generators.values():
        await generator.aclose()


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
