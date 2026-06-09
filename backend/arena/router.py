import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from backend.arena.captcha import generate_challenge
from backend.arena.dependencies import ComparisonMetadataAnno, RateLimitGuard
from backend.arena.models import AddFirstTextBody, AddTextBody
from backend.arena.reveal import RevealData, get_reveal_data
from backend.arena.services.comparison import (
    create_comparison,
    read_comparison,
    update_comparison_error,
    update_comparison_llm_id,
)
from backend.arena.services.turn import add_turn, update_turn, update_turn_vote
from backend.arena.session import (
    increment_custom_selections,
    increment_input_chars,
    is_custom_selection_ratelimited,
    store_comparison_metadata,
)
from backend.arena.streaming.ask import ask_llms
from backend.arena.streaming.events import create_sse_response, format_sse_event
from backend.arena.web_search import search_web
from backend.llms.data import get_llms_data, pick_replacement_model
from backend.utils.user import get_ip, get_matomo_tracker_from_cookies
from utils.database.models import (
    ComparisonCreate,
    ComparisonPublic,
    ComparisonRead,
    TurnPublic,
    TurnVoteAnnotate,
    TurnVoteChoice,
)

logger = logging.getLogger("languia")

router = APIRouter(
    prefix="/arena",
    tags=["arena"],
)


# FIXME log Comparison session data (ip, portal, cohorts, conv id) in routes?


@router.get("/challenge")
async def get_challenge() -> dict:
    """Generate a new Altcha proof-of-work challenge."""
    return generate_challenge()


@router.post("/add_first_text", dependencies=[RateLimitGuard])
async def add_first_text(args: AddFirstTextBody, request: Request) -> StreamingResponse:
    """
    Process user's first message and initiate Comparison.

    This is the main handler for the send button click. It:
    1. Selects two LLMs to compare based on mode
    2. Initializes and save Comparison for both LLMs with a first empty Turn
    4. Streams responses from both LLMs in parallel
    5. Save the completed Turn if everything went well

    Args:
        args: Request body with prompt, mode, optional custom model selection, etc.
        request: FastAPI request

    Returns:
        StreamingResponse: Server-Sent Events stream with LLM responses

    Raises:
        HTTPException: If rate limiting triggered or validation fails
    """
    logger.info(
        f"'/add_first_text' called with: {args.model_dump_json()}",
        extra={"request": request},
    )

    if args.mode == "custom" and args.custom_models_selection:
        ip = get_ip(request)
        if is_custom_selection_ratelimited(ip):
            logger.error(
                f"Too many custom model selections for ip {ip}",
                extra={"request": request},
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate_limit_custom_selection",
            )
        increment_custom_selections(ip)

    # Select LLMs
    llms_data = get_llms_data()
    llm_a_id, llm_b_id = llms_data.pick_two(args.mode, args.custom_models_selection)

    logger.info(
        f"Selected LLMs: '{llm_a_id}' vs '{llm_b_id}'", extra={"request": request}
    )

    web_search_results = None
    if args.web_search:
        web_search_results = await search_web(args.prompt_value)
        if web_search_results:
            logger.info("Web search returned context", extra={"request": request})

    # Initialize comparison and save it to db
    comparison = await create_comparison(
        ComparisonCreate(
            ip=get_ip(request),
            visitor_id=get_matomo_tracker_from_cookies(request.cookies),
            cohorts=args.cohorts,
            mode=args.mode,
            custom_models_selection=args.custom_models_selection,
            llm_id_a=llm_a_id,
            llm_id_b=llm_b_id,
        )
    )

    logger.info(
        f"Saved partial Comparison with id '{comparison.id}'",
        extra={"request": request},
    )

    # Stream responses
    async def event_stream(comparison: ComparisonRead) -> AsyncGenerator[str]:
        yield format_sse_event(
            {
                "type": "init",
                "comparison": ComparisonPublic.model_validate(comparison),
            }
        )

        # Add first turn and save it to db (to at least save the user prompt)
        comparison, turn = await add_turn(
            comparison.id, args.prompt_value, web_search_results
        )
        store_comparison_metadata(comparison.id, is_streaming=True)

        yield format_sse_event({"type": "add", "turn": TurnPublic.model_validate(turn)})

        # Stream both model responses
        async for chunk in ask_llms(comparison, turn, request):
            yield format_sse_event(chunk)

        if not comparison.error:
            # Increment input chars for pricey llms
            for llm_id in [comparison.llm_id_a, comparison.llm_id_b]:
                if llm_id in llms_data.pricey_models:
                    increment_input_chars(get_ip(request), len(args.prompt_value))

            await update_turn(turn.id, turn.llm_msg_a, turn.llm_msg_b)

        store_comparison_metadata(comparison.id, is_streaming=False)

    return create_sse_response(event_stream(comparison))


@router.post("/add_text", dependencies=[RateLimitGuard])
async def add_text(
    args: AddTextBody,
    metadata: ComparisonMetadataAnno,
    request: Request,
) -> StreamingResponse:
    """
    Add a follow-up message to an existing Comparison.

    It:
    1. Add a new empty Turn
    2. Streams responses from both LLMs in parallel
    3. Save the completed Turn if everything went well

    Args:
        args: Request body with message content
        metadata: Comparison metadata stored in redis
        request: FastAPI request for logging

    Returns:
        StreamingResponse: Server-Sent Events stream with LLM responses

    Raises:
        HTTPException: If Comparison not found or rate limiting triggered
    """
    logger.info(
        f"'/add_text' on comparison '{metadata.id}' called with: {args.model_dump_json()}",
        extra={"request": request},
    )

    # Assert last turn has vote

    # Stream responses
    async def event_stream() -> AsyncGenerator[str]:
        # Add new turn and save it to db (to at least save the user prompt)
        comparison, turn = await add_turn(metadata.id, args.message)
        store_comparison_metadata(comparison.id, is_streaming=True)

        yield format_sse_event({"type": "add", "turn": TurnPublic.model_validate(turn)})

        # Stream both model responses
        async for chunk in ask_llms(comparison, turn, request):
            yield format_sse_event(chunk)

        if not comparison.error:
            llms_data = get_llms_data()
            # Increment input chars for pricey llms
            for llm_id in [comparison.llm_id_a, comparison.llm_id_b]:
                if llm_id in llms_data.pricey_models:
                    increment_input_chars(get_ip(request), len(args.message))

            await update_turn(turn.id, turn.llm_msg_a, turn.llm_msg_b)

        store_comparison_metadata(comparison.id, is_streaming=False)

    return create_sse_response(event_stream())


@router.post("/retry", dependencies=[RateLimitGuard])
async def retry(
    metadata: ComparisonMetadataAnno,
    request: Request,
) -> StreamingResponse:
    """
    Retry generating the last LLM responses.

    Expects that at least the user message is present in last turn.
    Reroll a failing LLM if possible.

    Args:
        metadata: Comparison metadata stored in redis
        request: FastAPI request for logging

    Returns:
        StreamingResponse: Server-Sent Events stream with LLM responses

    Raises:
        HTTPException: If session not found or rate limiting triggered
    """
    logger.info(f"'/retry' on comparison '{metadata.id}'", extra={"request": request})

    comparison = await read_comparison(metadata.id)
    turn = comparison.turns[-1]

    if turn.user_msg is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Il n'est pas possible de réessayer, veuillez recharger la page.",
        )

    # If comparison has not yet trully started
    if comparison.error and len(comparison.turns) == 1:
        # if error is from a specific model, reroll it
        if pos := comparison.error.pos:
            if comparison.mode != "custom" and comparison.error.is_timeout:
                # Another timeout error occured even tho llms have been rerolled already
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Il n'est pas possible de réessayer, veuillez recharger la page.",
                )

            failing_llm_id = getattr(comparison, f"llm_id_{pos}")
            if new_llm_id := pick_replacement_model(comparison, pos):
                await update_comparison_llm_id(comparison, pos, new_llm_id)
                logger.warning(f"Swapped LLM '{failing_llm_id}' to '{new_llm_id}'")

    await update_comparison_error(comparison, None)

    store_comparison_metadata(comparison.id, is_streaming=True)

    logger.info(
        f"retry with user message: {turn.user_msg.content}",
        extra={"request": request},
    )

    # Re-stream responses
    async def event_stream(comparison: ComparisonRead) -> AsyncGenerator[str]:
        yield format_sse_event(
            {"type": "update", "turn": TurnPublic.model_validate(turn)}
        )

        # Stream both model responses
        async for chunk in ask_llms(comparison, turn, request):
            yield format_sse_event(chunk)

        if not comparison.error:
            llms_data = get_llms_data()
            # Increment input chars for pricey llms
            for llm_id in [comparison.llm_id_a, comparison.llm_id_b]:
                if llm_id in llms_data.pricey_models:
                    increment_input_chars(get_ip(request), len(turn.user_msg.content))

            await update_turn(turn.id, turn.llm_msg_a, turn.llm_msg_b)

        store_comparison_metadata(comparison.id, is_streaming=False)

    return create_sse_response(event_stream(comparison))


@router.post("/vote")
async def vote(
    vote: TurnVoteChoice | TurnVoteAnnotate,
    metadata: ComparisonMetadataAnno,
    request: Request,
) -> None:
    """
    Submit a vote choice or annotations.
    Vote choice should happen once per turn on last turn.
    Vote annotations can be updated multiple times and relate to one LLM pos only.

    Args:
        vote: Request body with vote data (choice or annotations)
        metadata: Comparison metadata stored in redis
        request: FastAPI request for logging

    Raises:
        HTTPException: If Comparison not found or forbidden vote attempts.
    """
    logger.info(
        f"'/vote' on comparison '{metadata.id}' called with: {vote.model_dump_json()}",
        extra={"request": request},
    )

    comparison = await read_comparison(metadata.id)
    turn = next((turn for turn in comparison.turns if turn.id == vote.turn_id), None)

    if not turn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Turn not found."
        )
    if turn != comparison.turns[-1]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Can vote only for last turn."
        )

    if comparison.error or not turn.llm_msg_a or not turn.llm_msg_b:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can't vote for unfinished turn.",
        )

    if isinstance(vote, TurnVoteChoice) and turn.choice is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Already made a choice."
        )
    if (isinstance(vote, TurnVoteAnnotate)) and turn.choice is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Have to make a choice before annotating.",
        )

    await update_turn_vote(turn.id, vote)


@router.get("/reveal")
async def reveal(metadata: ComparisonMetadataAnno, request: Request) -> RevealData:
    """
    Get reveal data for a Comparison.

    Args:
        metadata: Comparison metadata stored in redis
        request: FastAPI request for logging

    Returns:
        dict: Reveal data with LLM definitions and consumptions

    Raises:
        HTTPException: If Comparison not found or no vote.
    """
    logger.info(f"[REVEAL] comparison '{metadata.id}'", extra={"request": request})
    comparison = await read_comparison(metadata.id)
    last_turn = comparison.turns[-1]

    if last_turn.choice is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Have to make a choice before reveal.",
        )

    # Return computed reveal data with environmental impact
    return get_reveal_data(comparison)
