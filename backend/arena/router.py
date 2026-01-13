import logging
from typing import Annotated, TypedDict

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.arena.models import (
    AssistantMessage,
    Conversations,
    ReactionData,
    ReactRequest,
    RevealData,
    UserMessage,
    VoteRequest,
    create_conversations,
)
from backend.arena.persistence import (
    delete_reaction,
    record_conversations,
    record_reaction,
    record_vote,
)
from backend.arena.reveal import get_reveal_data
from backend.arena.session import (
    create_session,
    retrieve_session_conversations,
    store_session_conversations,
    update_session_conversations,
)
from backend.arena.streaming import create_sse_response, stream_both_responses
from backend.config import (
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
    DEFAULT_SELECTION_MODE,
    CustomModelsSelection,
    SelectionMode,
)
from backend.errors import Errors
from backend.language_models.data import get_models
from backend.session import is_ratelimited
from backend.utils.countries import CountryPortalAnno
from backend.utils.user import get_ip, get_matomo_tracker_from_cookies

logger = logging.getLogger("languia")

router = APIRouter(
    prefix="/arena",
    tags=["arena"],
)


# Dependencies


def assert_not_rate_limited(request: Request) -> None:
    """Dependency to check rate limiting based on IP address."""
    ip = get_ip(request)

    if is_ratelimited(ip):
        logger.error(
            f"Too much text submitted to pricey models for ip {ip}",
            extra={"request": request},
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=Errors.RATE_LIMITED.name,
        )


def get_session_hash(session_hash: str = Header(..., alias="X-Session-Hash")) -> str:
    """
    Dependency to extract and validate session hash from headers.

    Args:
        session_hash: Session identifier from X-Session-Hash header

    Returns:
        str: Validated session hash

    Raises:
        HTTPException: If session hash is missing or invalid
    """
    if not session_hash or len(session_hash) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing session hash"
        )
    return session_hash


def get_conversations(session_hash: str = Depends(get_session_hash)) -> Conversations:
    try:
        return Conversations.from_session(session_hash)
    except Exception as e:
        # FIXME raise different errors depending on problem
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conversations '{session_hash}' couldn't be found or parsed: {str(e)}",
        )


ConversationsAnno = Annotated[Conversations, Depends(get_conversations)]


class AddFirstTextBody(BaseModel):
    prompt_value: str = Field(min_length=1, max_length=BLIND_MODE_INPUT_CHAR_LEN_LIMIT)
    mode: SelectionMode = DEFAULT_SELECTION_MODE
    custom_models_selection: CustomModelsSelection = None
    country_portal: CountryPortalAnno
    # We force cohorts not to be None to make sure cohorts detection has been called on frontend
    cohorts: str


@router.post("/add_first_text", dependencies=[Depends(assert_not_rate_limited)])
async def add_first_text(args: AddFirstTextBody, request: Request):
    """
    Process user's first message and initiate model comparison.

    This is the main handler for the send button click. It:
    1. Creates a new session
    2. Selects two models to compare based on mode
    3. Initializes conversations for both models
    4. Streams responses from both models in parallel

    Args:
        args: Request body with prompt, mode, and optional custom model selection
        request: FastAPI request for logging and rate limiting

    Returns:
        StreamingResponse: Server-Sent Events stream with model responses

    Raises:
        HTTPException: If rate limiting triggered or validation fails
    """
    logger.info("chose mode: " + args.mode, extra={"request": request})
    logger.info(
        "custom_models_selection: " + str(args.custom_models_selection),
        extra={"request": request},
    )

    # Select models
    models = get_models()
    model_a_id, model_b_id = models.pick_two(args.mode, args.custom_models_selection)

    logger.info(
        f"Selected models: {model_a_id} vs {model_b_id}", extra={"request": request}
    )

    # Create new session
    session_hash = create_session()

    # Initialize conversations using Pydantic models
    conversations = create_conversations(
        llm_id_a=model_a_id,
        llm_id_b=model_b_id,
        args=args,
        category=None,  # FIXME category?
        session_hash=session_hash,
        ip=get_ip(request),
        visitor_id=get_matomo_tracker_from_cookies(request.cookies),
    )

    # Store Conversations to redis/db/logs
    conversations.store_to_session()
    # FIXME do we really want to store the conversations to db already?
    record_conversations(conversations)

    # Stream responses
    async def event_stream():
        # Send session hash first
        import json

        yield f"data: {json.dumps({'type': 'init', 'session_hash': session_hash})}\n\n"

        # Stream both model responses
        async for chunk in stream_both_responses(conversations, request):
            yield chunk

        # After streaming completes, store Conversations to redis/db/logs
        conversations.store_to_session()
        record_conversations(conversations)

    return create_sse_response(event_stream())


class AddTextBody(BaseModel):
    """Request body for add_text endpoint."""

    message: str = Field(min_length=1)


@router.post("/add_text", dependencies=[Depends(assert_not_rate_limited)])
async def add_text(
    args: AddTextBody,
    conversations: ConversationsAnno,
    request: Request,
):
    """
    Add a follow-up message to an existing conversation.

    Args:
        args: Request body with message content
        conversations: Conversations from session_hash
        request: FastAPI request for logging

    Returns:
        StreamingResponse: SSE stream with both model responses

    Raises:
        HTTPException: If session not found or rate limiting triggered
    """
    logger.info(
        f"[ADD_TEXT] session={conversations.session_hash}, message_len={len(args.message)}",
        extra={"request": request},
    )

    # Add user message to both conversations
    user_message = UserMessage(content=args.message)
    conversations.conversation_a.messages.append(user_message)
    conversations.conversation_b.messages.append(user_message)

    # Store Conversations to redis/db/logs
    conversations.store_to_session()
    # FIXME do we really want to store the conversations to db already?
    record_conversations(conversations)

    # Stream responses
    async def event_stream():
        async for chunk in stream_both_responses(conversations, request):
            yield chunk

        # After streaming completes, store Conversations to redis/db/logs
        conversations.store_to_session()
        record_conversations(conversations)

    return create_sse_response(event_stream())


@router.post("/retry", dependencies=[Depends(assert_not_rate_limited)])
async def retry(
    conversations: ConversationsAnno,
    request: Request,
):
    """
    Retry generating the last bot response.

    Removes the last assistant messages and re-generates them.

    Args:
        conversations: Conversations from session_hash
        request: FastAPI request for logging

    Returns:
        StreamingResponse: SSE stream with new model responses

    Raises:
        HTTPException: If session not found or rate limiting triggered
    """
    logger.info(
        f"[RETRY] session={conversations.session_hash}", extra={"request": request}
    )

    conv_a = conversations.conversation_a
    conv_b = conversations.conversation_b
    # Remove last assistant messages
    if isinstance(conv_a.messages[-1], AssistantMessage) and isinstance(
        conv_b.messages[-1], AssistantMessage
    ):
        conv_a.messages = conv_a.messages[:-1]
        conv_b.messages = conv_b.messages[:-1]

    if not (
        isinstance(conv_a.messages[-1], UserMessage)
        and isinstance(conv_b.messages[-1], UserMessage)
    ):
        raise Exception(
            "Il n'est pas possible de réessayer, veuillez recharger la page."
        )

    # Store Conversations to redis/db/logs
    conversations.store_to_session()
    # FIXME do we really want to store the conversations to db already?
    record_conversations(conversations)

    # Re-stream responses
    async def event_stream():
        async for chunk in stream_both_responses(conversations, request):
            yield chunk

        # After streaming completes, store Conversations to redis/db/logs
        conversations.store_to_session()
        record_conversations(conversations)

    return create_sse_response(event_stream())


ReactReturnType = TypedDict("ReactReturnType", {"reaction": ReactionData | None})


@router.post("/react")
async def react(
    react_request: ReactRequest,
    conversations: ConversationsAnno,
    request: Request,
) -> ReactReturnType:
    """
    Update reaction (like/dislike) for a specific message.

    Args:
        react_request: Request body with reaction data
        conversations: Conversations from session_hash
        request: FastAPI request for logging

    Returns:
        dict: reaction data

    Raises:
        HTTPException: If session not found
    """

    logger.info(
        f"[REACT] session={conversations.session_hash}, reaction={react_request.model_dump()}",
        extra={"request": request},
    )

    conv = (
        conversations.conversation_a
        if react_request.bot == "a"
        else conversations.conversation_b
    )

    # Get real message index from front which is the message index without counting system message
    msg_index = (
        react_request.index if not conv.has_system_msg else react_request.index + 1
    )
    message = conv.messages[msg_index] if len(conv.messages) > msg_index else None

    if not message or not isinstance(message, AssistantMessage):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assistant message not found"
        )

    if react_request.liked is None:
        # A reaction has been undone, remove it from its message and db
        message.reaction = None
        # Store conversations with removed reaction
        conversations.store_to_session()
        # Delete db reaction
        delete_reaction(conv, msg_index)

        return {"reaction": None}

    # Build final reaction data
    # FIXME replace reaction.index with msg_index?
    reaction_data = ReactionData.model_validate(react_request, from_attributes=True)

    message.reaction = reaction_data
    # Store conversations with updated reaction to redis
    conversations.store_to_session()
    # Store reaction to db/logs
    reaction_record = record_reaction(
        conversations=conversations,
        reaction=reaction_data,
        msg_index=msg_index,
        chatbot_index=react_request.index,
        request=request,
    )

    return {"reaction": reaction_data}


@router.post("/vote")
async def vote(
    vote_request: VoteRequest,
    conversations: ConversationsAnno,
    request: Request,
) -> RevealData:
    """
    Submit a vote after conversation and reveal model identities.

    Saves the vote to database and returns reveal data.

    Args:
        vote_request: Request body with vote data
        conversations: Conversations from session_hash
        request: FastAPI request for logging

    Returns:
        dict: Reveal data with model names, metadata, and environmental stats

    Raises:
        HTTPException: If session not found
    """
    from backend.arena.session import retrieve_session_conversations
    from backend.config import settings

    logger.info(
        f"[VOTE] session={conversations.session_hash}, chosen={vote_request.chosen_llm}",
        extra={"request": request},
    )

    # FIXME not sure it is usefull to save vote to Conversations
    conversations.vote = vote_request
    # Store conversations with updated vote to redis
    conversations.store_to_session()

    # Save vote to database with prefs and comments
    record_vote(
        conversations=conversations,
        vote=vote_request,
        request=request,
    )

    # Return computed reveal data with environmental impact
    return get_reveal_data(conversations, vote_request.chosen_llm)


@router.get("/reveal/{session_hash}")
async def reveal(session_hash: str, request: Request) -> RevealData:
    """
    Get reveal data for a session (model identities and metadata).

    Args:
        session_hash: Session identifier from path
        request: FastAPI request for logging

    Returns:
        dict: Reveal data with model names and metadata

    Raises:
        HTTPException: If session not found
    """
    logger.info(f"[REVEAL] session={session_hash}", extra={"request": request})

    # Retrieve conversations
    try:
        conversations = Conversations.from_session(session_hash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Return computed reveal data with environmental impact
    return get_reveal_data(conversations, "both_equal")
