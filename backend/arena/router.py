import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, AsyncGenerator, Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from backend.arena.captcha import generate_challenge, solved_max_number
from backend.arena.checks import (
    PromptCheckResult,
    count_warning_shown,
    drop_flagged_results,
    issue_warning_token,
    run_prompt_check,
)
from backend.arena.limits import (
    Allowance,
    AllowanceSpent,
    Identity,
    message_cost,
    read_status,
    reserve,
)
from backend.arena.models import (
    AddFirstTextBody,
    AddTextBody,
    LimitRefusal,
    RetryBody,
)
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
    clear_unvoted,
    increment_blocked_prompts,
    increment_sent_warnings,
    increment_unvoted,
    is_block_cooldown,
    is_warning_cooldown,
    retreive_comparison_metadata,
    store_comparison_metadata,
    unvoted_comparisons,
)
from backend.arena.spam_detection import is_spam
from backend.arena.streaming import (
    create_sse_response,
    format_sse_event,
    stream_comparison_messages,
)
from backend.arena.web_search import keep_search_results, search_web
from backend.auth.dependencies import OptionalUser, RequiredAnomymous, RequiredUser
from backend.auth.services import get_current_terms_acceptance_version
from backend.config import (
    ALTCHA_HARD_MAX_NUMBER,
    ALTCHA_MAX_NUMBER,
    ALTCHA_UNVOTED_COMPARISONS,
    MAX_TURNS_PER_COMPARISON,
)
from backend.errors import LimitReachedError
from backend.llms.data import LLMsData, get_llms_data, pick_replacement_model
from backend.utils.user import get_ip
from backend.vote_tags.services import (
    UnknownVoteTagError,
    VoteTagSignMismatchError,
    check_vote_tags,
)
from utils.database.models import (
    ComparisonCreate,
    ComparisonPublic,
    ComparisonRead,
    TurnPublic,
    TurnVoteAnnotate,
    TurnVoteChoice,
)
from utils.database.prompt_checks import save_prompt_check_result

logger = logging.getLogger("languia")

router = APIRouter(
    prefix="/arena",
    tags=["arena"],
)


# Dependencies


def limit_refusal(spent: Sequence[Allowance]) -> LimitReachedError:
    """
    What the person is told for these spent allowances: the one that lifts
    last, since that is when they can go on.
    """
    last = max(spent, key=lambda allowance: allowance.resets_in or 0)
    resets_at = (
        datetime.now(timezone.utc).replace(microsecond=0)
        + timedelta(seconds=last.resets_in)
        if last.resets_in is not None
        else None
    )
    return LimitReachedError(
        "allowance_spent" if last.pool == "all" else "expensive_allowance_spent",
        LimitRefusal(
            scope="session" if last.scope == "session" else "network",
            resets_at=resets_at,
            resets_in=last.resets_in,
        ),
    )


def assert_not_rate_limited(
    anonymous_user_hash: RequiredAnomymous, request: Request
) -> None:
    """Rate-limit model usage per anonymous session, with the IP as a backstop
    for clients that drop the session cookie."""
    spent = read_status(Identity.of(anonymous_user_hash, get_ip(request))).spent
    if spent:
        logger.error(
            "Too much text submitted to the models for anonymous session",
            extra={"request": request},
        )
        raise limit_refusal(spent)


def charge_budget(
    text: str,
    llm_ids: tuple[UUID, UUID],
    llms_data: LLMsData,
    anonymous_user_hash: str,
    request: Request,
) -> None:
    """
    Spend the message's characters against the session and IP budgets before
    any model is called. The charge used to wait for a full, error-free answer,
    so a client that hung up halfway, or sent many requests at once, never paid.
    No refund when a model then fails: an error a client can provoke would buy
    whatever the models had already written.
    """
    who = Identity.of(anonymous_user_hash, get_ip(request))
    try:
        reserve(who, message_cost(text, llm_ids, llms_data))
    except AllowanceSpent as error:
        logger.error(
            "Too much text submitted to the models for anonymous session",
            extra={"request": request},
        )
        raise limit_refusal(error.spent)


def assert_not_block_cooldown(
    anonymous_user_hash: RequiredAnomymous, request: Request
) -> None:
    """Cool down IPs that keep tripping the prompt check, and sessions that
    keep sending warned prompts anyway."""
    if is_block_cooldown(get_ip(request)) or is_warning_cooldown(anonymous_user_hash):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="block_cooldown",
        )


def assert_captcha_paid(token: str, session: str) -> None:
    """
    Refuse an easy captcha from a session that has to solve hard ones. One
    comparison of slack over `get_challenge`: the browser fetches its next
    challenge while the comparison that crosses the line is being created, so
    that challenge may still be an easy one.
    """
    if (
        unvoted_comparisons(session) > ALTCHA_UNVOTED_COMPARISONS
        and solved_max_number(token) < ALTCHA_HARD_MAX_NUMBER
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {
                    "loc": ["body", "altcha_token"],
                    "msg": "captcha_failed",
                    "type": "value_error",
                }
            ],
        )


async def run_checks(
    text: str,
    field: str,
    request: Request,
    warning_token: str | None = None,
    context: Sequence[str] = (),
    session: str = "",
) -> PromptCheckResult | None:
    """
    Run the spam patterns and the prompt check on a user message. Raises a 422
    (shaped like a Pydantic validation error so the frontend renders it under
    the input) when a pattern matches or a category set to `block` refuses the
    prompt, otherwise returns the verdict, to warn the user about and to
    persist on the turn.
    """
    if is_spam(text):
        # Counted like a block, so a script probing for a spelling the
        # patterns miss runs into the cooldown instead of trying forever.
        increment_blocked_prompts(get_ip(request))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {"loc": ["body", field], "msg": "spam_detected", "type": "value_error"}
            ],
        )

    result = await run_prompt_check(
        text, request, warning_token=warning_token, context=context
    )
    if result and result.decision == "blocked":
        # A prompt that could not be checked is refused below but not charged:
        # the failure is ours, and it gets an attacker nothing.
        increment_blocked_prompts(get_ip(request))
    if result and result.decision == "warned" and result.user_proceeded:
        # A script reads the warning token off the response and resends, so
        # without a cost `warn` would stop no one but people. Charged to the
        # session rather than the IP, so people sharing one IP do not pay for
        # each other.
        increment_sent_warnings(session)
    if result and result.block_message:
        result = await save_prompt_check_result(result)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {
                    "loc": ["body", field],
                    "msg": result.block_message,
                    "type": "value_error",
                }
            ],
        )
    return result


def warning_response(result: PromptCheckResult, text: str) -> StreamingResponse:
    """
    Stream a single 'warning' event and stop. Nothing is created and no model is
    called: the browser asks the user to confirm, and sends the prompt again with
    the one-time `warning_token` if they go ahead.
    """
    count_warning_shown()
    token = issue_warning_token(text, result.model)
    warnings = [{"kind": "prompt_check", "message": result.message or ""}]

    async def event_stream() -> AsyncGenerator[str]:
        yield format_sse_event(
            {"type": "warning", "warnings": warnings, "warning_token": token}
        )

    return create_sse_response(event_stream())


def get_comparison_metadata(comparison_id: UUID) -> ComparisonMetadata | None:
    try:
        metadata = retreive_comparison_metadata(comparison_id)
    except Exception as e:
        return None

    # For any arena view, raise error if chat responses are not yet finished
    if metadata.is_streaming:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="comparison_streaming",
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
async def get_challenge(anonymous_user_hash: RequiredAnomymous) -> dict:
    """Generate a new Altcha proof-of-work challenge, a harder one for a session
    that keeps starting comparisons without voting."""
    if unvoted_comparisons(anonymous_user_hash) >= ALTCHA_UNVOTED_COMPARISONS:
        return generate_challenge(ALTCHA_HARD_MAX_NUMBER)
    return generate_challenge(ALTCHA_MAX_NUMBER)


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
    participation_terms_version = await get_current_terms_acceptance_version(
        user_id=user.id if user else None,
        anonymous_user_hash=anonymous_user_hash,
    )
    if not participation_terms_version:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Accept the terms in force before participating.",
        )

    # Prompts stay out of the logs. They go to a file and to Loki, the in-app
    # notice tells people not to put personal data in them, and the operators
    # who read the logs are not the audience the user wrote for. What is left is
    # the shape of the request, which is what the logs are read for anyway.
    logger.info(
        f"'/add_first_text' called in mode '{args.mode}' ({len(args.prompt_value)} chars, web_search={args.web_search})",
        extra={"request": request},
    )

    assert_captcha_paid(args.altcha_token, anonymous_user_hash)
    check = await run_checks(
        args.prompt_value,
        "prompt_value",
        request,
        args.warning_token,
        session=anonymous_user_hash,
    )
    if check and check.pending_warning:
        return warning_response(check, args.prompt_value)

    # Select LLMs
    llms_data = await get_llms_data()
    llm_a_id, llm_b_id = llms_data.pick_two(args.mode, args.custom_models_selection)

    logger.info(
        f"Selected LLMs: '{llm_a_id}' vs '{llm_b_id}'", extra={"request": request}
    )

    charge_budget(
        args.prompt_value, (llm_a_id, llm_b_id), llms_data, anonymous_user_hash, request
    )
    check = (await save_prompt_check_result(check)) if check else None

    web_search_results = None
    if args.web_search:
        web_search_results = await search_web(args.prompt_value)
        if web_search_results:
            web_search_results = keep_search_results(
                args.prompt_value, web_search_results
            )
        if web_search_results:
            web_search_results = await drop_flagged_results(web_search_results)
        if web_search_results:
            logger.info("Web search returned context", extra={"request": request})

    # Initialize comparison and save it to db
    comparison = await create_comparison(
        ComparisonCreate(
            ip=get_ip(request),
            anonymous_user_hash=anonymous_user_hash if not user else None,
            user_id=user.id if user else None,
            participation_terms_version=participation_terms_version,
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
    # Only new comparisons count. Someone deep in one conversation is using the
    # arena; someone opening comparison after comparison and never voting is
    # more likely using the models for free.
    increment_unvoted(anonymous_user_hash)

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
            prompt_check_result=check,
        )
        store_comparison_metadata(comparison.id, is_streaming=True)

        try:
            yield format_sse_event(
                {"type": "add", "turn": TurnPublic.model_validate(turn)}
            )

            # Stream both model responses
            async for chunk in stream_comparison_messages(comparison, turn, request):
                yield format_sse_event(chunk)

            if not comparison.error:
                await update_turn(turn.id, turn.llm_msg_a, turn.llm_msg_b)
        finally:
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
        f"'/add_text' on comparison '{comparison_.id}' ({len(args.message)} chars)",
        extra={"request": request},
    )

    # Each turn resends the whole transcript to both models, so the cost of a
    # conversation grows with its square. `/retry` re-runs the last turn rather
    # than adding one, so this is the only place the transcript can grow.
    if len(comparison_.turns) >= MAX_TURNS_PER_COMPARISON:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="max_turns_reached",
        )

    assert_captcha_paid(args.altcha_token, anonymous_user_hash)
    check = await run_checks(
        args.message,
        "message",
        request,
        args.warning_token,
        context=[turn.user_msg.content for turn in comparison_.turns],
        session=anonymous_user_hash,
    )
    if check and check.pending_warning:
        return warning_response(check, args.message)

    charge_budget(
        args.message,
        (comparison_.llm_id_a, comparison_.llm_id_b),
        await get_llms_data(),
        anonymous_user_hash,
        request,
    )
    check = (await save_prompt_check_result(check)) if check else None

    # Assert last turn has vote

    # Stream responses
    async def event_stream() -> AsyncGenerator[str]:
        # Add new turn and save it to db (to at least save the user prompt)
        comparison, turn = await add_comparison_turn(
            comparison_.id,
            args.message,
            prompt_check_result=check,
        )
        store_comparison_metadata(comparison.id, is_streaming=True)

        try:
            yield format_sse_event(
                {"type": "add", "turn": TurnPublic.model_validate(turn)}
            )

            # Stream both model responses
            async for chunk in stream_comparison_messages(comparison, turn, request):
                yield format_sse_event(chunk)

            if not comparison.error:
                await update_turn(turn.id, turn.llm_msg_a, turn.llm_msg_b)
        finally:
            store_comparison_metadata(comparison.id, is_streaming=False)

    return create_sse_response(event_stream())


@router.post(
    "/retry/{comparison_id}",
    dependencies=[Depends(assert_not_rate_limited), Depends(assert_not_block_cooldown)],
)
async def retry(
    comparison: ComparisonAnno,
    args: RetryBody,
    anonymous_user_hash: RequiredAnomymous,
    request: Request,
) -> StreamingResponse:
    """
    Retry generating the last LLM responses.

    Expects that at least the user message is present in last turn.
    Reroll a failing LLM if possible.

    Args:
        comparison: linked Comparison
        args: Request body with the captcha solution
        request: FastAPI request for logging

    Returns:
        StreamingResponse: Server-Sent Events stream with LLM responses

    Raises:
        HTTPException: If session not found or rate limiting triggered
    """
    logger.info(f"'/retry' on comparison '{comparison.id}'", extra={"request": request})
    assert_captcha_paid(args.altcha_token, anonymous_user_hash)

    turn = comparison.turns[-1]

    # Only a turn that failed or never finished can be run again. Otherwise one
    # prompt that passed the check could be answered again and again, with no
    # captcha and no check in the way.
    finished = turn.llm_msg_a is not None and turn.llm_msg_b is not None
    if turn.user_msg is None or (finished and not comparison.error):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="retry_unavailable",
        )

    # If comparison has not yet trully started
    if comparison.error and len(comparison.turns) == 1:
        # if error is from a specific model, reroll it
        if pos := comparison.error.pos:
            if comparison.mode != "custom" and comparison.error.is_timeout:
                # Another timeout error occured even tho llms have been rerolled already
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="retry_unavailable",
                )

            failing_llm_id = getattr(comparison, f"llm_id_{pos}")
            if new_llm_id := await pick_replacement_model(comparison, pos):
                await update_comparison_llm_id(comparison, pos, new_llm_id)
                logger.warning(f"Swapped LLM '{failing_llm_id}' to '{new_llm_id}'")

    charge_budget(
        turn.user_msg.content,
        (comparison.llm_id_a, comparison.llm_id_b),
        await get_llms_data(),
        anonymous_user_hash,
        request,
    )

    await update_comparison_error(comparison, None)

    store_comparison_metadata(comparison.id, is_streaming=True)

    logger.info(
        f"retry on turn '{turn.id}'",
        extra={"request": request},
    )

    # Re-stream responses
    async def event_stream(comparison: ComparisonRead) -> AsyncGenerator[str]:
        yield format_sse_event(
            {"type": "update", "turn": TurnPublic.model_validate(turn)}
        )

        try:
            # Stream both model responses
            async for chunk in stream_comparison_messages(comparison, turn, request):
                yield format_sse_event(chunk)

            if not comparison.error:
                await update_turn(turn.id, turn.llm_msg_a, turn.llm_msg_b)
        finally:
            store_comparison_metadata(comparison.id, is_streaming=False)

    return create_sse_response(event_stream(comparison))


@router.post("/vote/{comparison_id}")
async def vote(
    comparison: ComparisonAnno,
    vote: TurnVoteChoice | TurnVoteAnnotate,
    anonymous_user_hash: RequiredAnomymous,
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
    # `vote.model_dump_json()` would carry the voter's free-text annotation.
    logger.info(
        f"'/vote' on comparison '{comparison.id}' for turn '{vote.turn_id}'",
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
    if isinstance(vote, TurnVoteAnnotate):
        if turn.choice is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Have to make a choice before annotating.",
            )
        try:
            await check_vote_tags(vote.keyword_annotations, turn.choice, vote.pos)
        except UnknownVoteTagError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown vote tag: {error}",
            ) from error
        except VoteTagSignMismatchError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Vote tag does not match the choice: {error}",
            ) from error

    await update_turn_vote(turn.id, vote)
    if isinstance(vote, TurnVoteChoice):
        clear_unvoted(anonymous_user_hash)


@router.post("/reveal/{comparison_id}")
async def reveal(
    comparison: ComparisonAnno,
    request: Request,
) -> RevealData:
    """
    Get reveal data for a Comparison.

    POST, not GET: it marks the comparison revealed, and a browser or a crawler
    is free to replay a GET.

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

    # Return computed reveal data with environmental impact. Counting the
    # tokens of a long conversation takes seconds, so it runs off the event
    # loop; the comparison is plain data by now, with no session behind it.
    return await asyncio.to_thread(get_reveal_data, comparison, llms_data)


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
