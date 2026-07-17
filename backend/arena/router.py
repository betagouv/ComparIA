import logging
from typing import Annotated, AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from backend.arena.captcha import generate_challenge
from backend.arena.models import AddFirstTextBody, AddTextBody
from backend.arena.moderation import GuardrailVerdict, check_prompt
from backend.arena.reveal import RevealData, get_reveal_data
from backend.arena.services import (
    add_comparison_turn,
    create_comparison,
    get_user_comparisons,
    merge_anonymous_comparisons,
    read_comparison,
    set_comparison_revealed,
    update_comparison_error,
    update_comparison_llm_id,
    update_turn,
    update_turn_vote,
)
from backend.arena.session import (
    ComparisonMetadata,
    increment_blocked_prompts,
    increment_input_chars,
    is_block_cooldown,
    is_ratelimited,
    retreive_comparison_metadata,
    store_comparison_metadata,
)
from backend.arena.streaming import (
    create_sse_response,
    format_sse_event,
    stream_comparison_messages,
)
from backend.arena.web_search import search_web
from backend.auth.dependencies import OptionalUser, RequiredAnomymous, RequiredUser
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


# Dependencies


def assert_not_rate_limited(
    anonymous_user_hash: RequiredAnomymous, request: Request
) -> None:
    """Rate-limit expensive-model usage per anonymous session (not per IP)."""
    if is_ratelimited(anonymous_user_hash):
        logger.error(
            "Too much text submitted to pricey models for anonymous session",
            extra={"request": request},
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Vous avez trop sollicité les modèles parmi les plus onéreux, veuillez réessayer dans quelques heures. Vous pouvez toujours solliciter des modèles plus petits.",
        )


def assert_not_block_cooldown(request: Request) -> None:
    """Cool down IPs that keep tripping the content-safety guardrail."""
    if is_block_cooldown(get_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de messages bloqués ont été envoyés depuis votre connexion. Veuillez patienter avant de réessayer.",
        )


async def run_guardrail(
    text: str, field: str, request: Request
) -> GuardrailVerdict | None:
    """
    Run the content-safety guardrail on a user prompt. Raises a 422 (shaped like
    a Pydantic validation error so the frontend renders it under the input) when
    the prompt is blocked, otherwise returns the verdict to persist on the turn.
    """
    verdict = await check_prompt(text, request)
    if verdict and verdict.should_block:
        increment_blocked_prompts(get_ip(request))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {
                    "loc": ["body", field],
                    "msg": verdict.block_message,
                    "type": "value_error",
                }
            ],
        )
    return verdict


def get_comparison_metadata(comparison_id: UUID) -> ComparisonMetadata | None:
    try:
        metadata = retreive_comparison_metadata(comparison_id)
    except Exception as e:
        return None

    # For any arena view, raise error if chat responses are not yet finished
    if metadata.is_streaming:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veuillez attendre la fin de la réponse des modèles.",
        )

    return metadata


async def get_comparison(
    comparison_id: UUID, user: OptionalUser, anonymous_user_hash: RequiredAnomymous
) -> ComparisonRead:
    """
    Query specified Comparison.

    Raises:
        HTTPException: If comparison doesn't exists, is already streamin or
        user id or anonymous user hash doesn't correspond to the Comparison.
    """
    get_comparison_metadata(comparison_id)  # check if is_streaming

    return await read_comparison(
        comparison_id, user.id if user else None, anonymous_user_hash
    )


ComparisonAnno = Annotated[ComparisonRead, Depends(get_comparison)]

# FIXME log Comparison session data (ip, portal, cohorts, conv id) in routes?


@router.get("/challenge")
async def get_challenge() -> dict:
    """Generate a new Altcha proof-of-work challenge."""
    return generate_challenge()


@router.post(
    "/add_first_text",
    dependencies=[Depends(assert_not_rate_limited), Depends(assert_not_block_cooldown)],
)
async def add_first_text(
    args: AddFirstTextBody,
    user: OptionalUser,
    anonymous_user_hash: RequiredAnomymous,
    request: Request,
) -> StreamingResponse:
    """
    Process user's first message and initiate Comparison.

    This is the main handler for the send button click. It:
    1. Selects two LLMs to compare based on mode
    2. Initializes and save Comparison for both LLMs with a first empty Turn
    4. Streams responses from both LLMs in parallel
    5. Save the completed Turn if everything went well

    Args:
        args: Request body with prompt, mode, optional custom model selection, etc.
        user: User if connected
        anonymous_user_hash: anonymous user hash from cookie
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

    guardrail = await run_guardrail(args.prompt_value, "prompt_value", request)

    # Select LLMs
    llms_data = await get_llms_data()
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
            anonymous_user_hash=anonymous_user_hash if not user else None,
            user_id=user.id if user else None,
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
                "comparison": ComparisonPublic.model_validate(
                    comparison, context={"llms_data": llms_data}
                ),
            }
        )

        # Add first turn and save it to db (to at least save the user prompt)
        comparison, turn = await add_comparison_turn(
            comparison.id,
            args.prompt_value,
            web_search_results,
            guardrail=guardrail.as_record() if guardrail else None,
        )
        store_comparison_metadata(comparison.id, is_streaming=True)

        yield format_sse_event({"type": "add", "turn": TurnPublic.model_validate(turn)})

        # Stream both model responses
        async for chunk in stream_comparison_messages(comparison, turn, request):
            yield format_sse_event(chunk)

        if not comparison.error:
            # Increment input chars for pricey llms
            for llm_id in [comparison.llm_id_a, comparison.llm_id_b]:
                if llm_id in llms_data.pricey_models:
                    increment_input_chars(anonymous_user_hash, len(args.prompt_value))

            await update_turn(turn.id, turn.llm_msg_a, turn.llm_msg_b)

        store_comparison_metadata(comparison.id, is_streaming=False)

    return create_sse_response(event_stream(comparison))


@router.post(
    "/add_text/{comparison_id}",
    dependencies=[Depends(assert_not_rate_limited), Depends(assert_not_block_cooldown)],
)
async def add_text(
    comparison_: ComparisonAnno,
    args: AddTextBody,
    anonymous_user_hash: RequiredAnomymous,
    request: Request,
) -> StreamingResponse:
    """
    Add a follow-up message to an existing Comparison.

    It:
    1. Add a new empty Turn
    2. Streams responses from both LLMs in parallel
    3. Save the completed Turn if everything went well

    Args:
        comparison: linked Comparison
        args: Request body with message content
        request: FastAPI request for logging

    Returns:
        StreamingResponse: Server-Sent Events stream with LLM responses

    Raises:
        HTTPException: If Comparison not found or rate limiting triggered
    """
    logger.info(
        f"'/add_text' on comparison '{comparison_.id}' called with: {args.model_dump_json()}",
        extra={"request": request},
    )

    guardrail = await run_guardrail(args.message, "message", request)

    # Assert last turn has vote

    # Stream responses
    async def event_stream() -> AsyncGenerator[str]:
        # Add new turn and save it to db (to at least save the user prompt)
        comparison, turn = await add_comparison_turn(
            comparison_.id,
            args.message,
            guardrail=guardrail.as_record() if guardrail else None,
        )
        store_comparison_metadata(comparison.id, is_streaming=True)

        yield format_sse_event({"type": "add", "turn": TurnPublic.model_validate(turn)})

        # Stream both model responses
        async for chunk in stream_comparison_messages(comparison, turn, request):
            yield format_sse_event(chunk)

        if not comparison.error:
            llms_data = await get_llms_data()
            # Increment input chars for pricey llms
            for llm_id in [comparison.llm_id_a, comparison.llm_id_b]:
                if llm_id in llms_data.pricey_models:
                    increment_input_chars(anonymous_user_hash, len(args.message))

            await update_turn(turn.id, turn.llm_msg_a, turn.llm_msg_b)

        store_comparison_metadata(comparison.id, is_streaming=False)

    return create_sse_response(event_stream())


@router.post("/retry/{comparison_id}", dependencies=[Depends(assert_not_rate_limited)])
async def retry(
    comparison: ComparisonAnno,
    anonymous_user_hash: RequiredAnomymous,
    request: Request,
) -> StreamingResponse:
    """
    Retry generating the last LLM responses.

    Expects that at least the user message is present in last turn.
    Reroll a failing LLM if possible.

    Args:
        comparison: linked Comparison
        request: FastAPI request for logging

    Returns:
        StreamingResponse: Server-Sent Events stream with LLM responses

    Raises:
        HTTPException: If session not found or rate limiting triggered
    """
    logger.info(f"'/retry' on comparison '{comparison.id}'", extra={"request": request})

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
            if new_llm_id := await pick_replacement_model(comparison, pos):
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
        async for chunk in stream_comparison_messages(comparison, turn, request):
            yield format_sse_event(chunk)

        if not comparison.error:
            llms_data = await get_llms_data()
            # Increment input chars for pricey llms
            for llm_id in [comparison.llm_id_a, comparison.llm_id_b]:
                if llm_id in llms_data.pricey_models:
                    increment_input_chars(
                        anonymous_user_hash, len(turn.user_msg.content)
                    )

            await update_turn(turn.id, turn.llm_msg_a, turn.llm_msg_b)

        store_comparison_metadata(comparison.id, is_streaming=False)

    return create_sse_response(event_stream(comparison))


@router.post("/vote/{comparison_id}")
async def vote(
    comparison: ComparisonAnno,
    vote: TurnVoteChoice | TurnVoteAnnotate,
    request: Request,
) -> None:
    """
    Submit a vote choice or annotations.
    Vote choice should happen once per turn on last turn.
    Vote annotations can be updated multiple times and relate to one LLM pos only.

    Args:
        comparison: linked Comparison
        vote: Request body with vote data (choice or annotations)
        request: FastAPI request for logging

    Raises:
        HTTPException: If Comparison not found or forbidden vote attempts.
    """
    logger.info(
        f"'/vote' on comparison '{comparison.id}' called with: {vote.model_dump_json()}",
        extra={"request": request},
    )

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


@router.get("/reveal/{comparison_id}")
async def reveal(
    comparison: ComparisonAnno,
    request: Request,
) -> RevealData:
    """
    Get reveal data for a Comparison.

    Args:
        comparison: linked Comparison
        request: FastAPI request for logging

    Returns:
        dict: Reveal data with LLM definitions and consumptions

    Raises:
        HTTPException: If Comparison not found or no vote.
    """
    logger.info(f"[REVEAL] comparison '{comparison.id}'", extra={"request": request})

    if comparison.revealed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Comparison has already been revealed.",
        )

    last_turn = comparison.turns[-1]
    if last_turn.choice is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Have to make a choice before reveal.",
        )

    await set_comparison_revealed(comparison.id)
    llms_data = await get_llms_data()

    # Return computed reveal data with environmental impact
    return get_reveal_data(comparison, llms_data)


@router.get("/comparison/list")
async def get_comparisons(
    user: OptionalUser,
    anonymous_user_hash: RequiredAnomymous,
    request: Request,
) -> list[ComparisonPublic]:
    """
    Get comparison list.

    Args:
        user: Authenticated user
        request: FastAPI request for logging

    Returns:
        list: list of user's Comparison if logged in.
    """
    user_id = user.id if user else None
    comparisons = await get_user_comparisons(user_id, anonymous_user_hash)

    return comparisons


@router.post("/comparison/merge")
async def merge_comparisons(
    user: RequiredUser,
    anonymous_user_hash: RequiredAnomymous,
    request: Request,
) -> None:
    await merge_anonymous_comparisons(user.id, anonymous_user_hash)
