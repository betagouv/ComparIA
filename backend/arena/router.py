import logging

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from backend.arena.models import (
    AssistantMessage,
    Conversations,
    ReactRequest,
    UserMessage,
    VoteRequest,
    create_conversations,
)
from backend.arena.persistence import record_conversations, record_reaction, record_vote
from backend.arena.session import (
    create_session,
    retrieve_session_conversations,
    store_session_conversations,
    update_session_conversations,
)
from backend.arena.streaming import create_sse_response, stream_both_responses
from backend.arena.utils import (
    deserialize_conversation_from_redis,
    serialize_conversation_for_redis,
)
from backend.config import (
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
    DEFAULT_SELECTION_MODE,
    SelectionMode,
)
from backend.errors import Errors
from backend.language_models.data import get_models
from backend.session import is_ratelimited
from backend.utils.user import get_ip

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
        raise HTTPException(status_code=429, detail=Errors.RATE_LIMITED.name)


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
        raise HTTPException(status_code=400, detail="Missing session hash")
    return session_hash


class AddFirstTextBody(BaseModel):
    prompt_value: str = Field(min_length=1, max_length=BLIND_MODE_INPUT_CHAR_LEN_LIMIT)
    mode: SelectionMode = DEFAULT_SELECTION_MODE
    custom_models_selection: tuple[str] | tuple[str, str] | None = None


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

    # Get LanguageModel objects from IDs
    llm_a = models.all[model_a_id]
    llm_b = models.all[model_b_id]

    # Initialize conversations using Pydantic models
    conversations = create_conversations(
        llm_a, llm_b, args.prompt_value, args.mode, category=None
    )  # FIXME category?

    # Store conversations in Redis
    conversations.store_to_session(session_hash)

    # Stream responses
    async def event_stream():
        # Send session hash first
        import json

        yield f"data: {json.dumps({'type': 'init', 'session_hash': session_hash})}\n\n"

        # Stream both model responses
        async for chunk in stream_both_responses(conversations, request):
            yield chunk

        # After streaming completes, archive conversation to Redis and database
        conversations.store_to_session(session_hash)

        try:
            conversation_record = record_conversations(
                conversations=conversations,
                session_hash=session_hash,
                request=request,
                locale="fr",  # FIXME
                cohorts_comma_separated="",  # FIXME
                custom_models_selection=args.custom_models_selection,
            )
            logger.info(
                f"[ADD_FIRST_TEXT] Archived conversation: {conversation_record['conversation_pair_id']}"
            )
        except Exception as e:
            # Log error but don't fail the streaming
            logger.error(
                f"[ADD_FIRST_TEXT] Error archiving conversation: {e}", exc_info=True
            )

    return create_sse_response(event_stream())


class AddTextBody(BaseModel):
    """Request body for add_text endpoint."""

    message: str = Field(min_length=1)


@router.post("/add_text", dependencies=[Depends(assert_not_rate_limited)])
async def add_text(
    args: AddTextBody,
    request: Request,
    session_hash: str = Depends(get_session_hash),
):
    """
    Add a follow-up message to an existing conversation.

    Args:
        args: Request body with message content
        request: FastAPI request for logging
        session_hash: Session identifier from X-Session-Hash header

    Returns:
        StreamingResponse: SSE stream with both model responses

    Raises:
        HTTPException: If session not found or rate limiting triggered
    """
    logger.info(
        f"[ADD_TEXT] session={session_hash}, message_len={len(args.message)}",
        extra={"request": request},
    )

    # Retrieve conversations from Redis
    try:
        conversations = Conversations.from_session(session_hash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Add user message to both conversations
    user_message = UserMessage(content=args.message)
    conversations.conversation_a.messages.append(user_message)
    conversations.conversation_b.messages.append(user_message)

    # Update in Redis
    conversations.store_to_session(session_hash)

    # Stream responses
    async def event_stream():
        async for chunk in stream_both_responses(conversations, request):
            yield chunk

        # After streaming completes, archive conversation to Redis and database
        conversations.store_to_session(session_hash)

        try:
            conversation_record = record_conversations(
                conversations=conversations,
                session_hash=session_hash,
                request=request,
                locale="fr",  # FIXME
                cohorts_comma_separated="",  # FIXME
            )
            logger.info(
                f"[ADD_TEXT] Archived conversation: {conversation_record['conversation_pair_id']}"
            )
        except Exception as e:
            # Log error but don't fail the streaming
            logger.error(f"[ADD_TEXT] Error archiving conversation: {e}", exc_info=True)

    return create_sse_response(event_stream())


@router.post("/retry", dependencies=[Depends(assert_not_rate_limited)])
async def retry(
    request: Request,
    session_hash: str = Depends(get_session_hash),
):
    """
    Retry generating the last bot response.

    Removes the last assistant messages and re-generates them.

    Args:
        request: FastAPI request for logging
        session_hash: Session identifier from X-Session-Hash header

    Returns:
        StreamingResponse: SSE stream with new model responses

    Raises:
        HTTPException: If session not found or rate limiting triggered
    """
    logger.info(f"[RETRY] session={session_hash}", extra={"request": request})

    # Retrieve conversations
    try:
        conversations = Conversations.from_session(session_hash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

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

    # Update in Redis
    conversations.store_to_session(session_hash)

    # Re-stream responses
    async def event_stream():
        async for chunk in stream_both_responses(conversations, request):
            yield chunk

        # After streaming completes, archive conversation to Redis and database
        conversations.store_to_session(session_hash)

        try:
            conversation_record = record_conversations(
                conversations=conversations,
                session_hash=session_hash,
                request=request,
                locale="fr",  # FIXME
                cohorts_comma_separated="",  # FIXME
            )
            logger.info(
                f"[RETRY] Archived conversation: {conversation_record['conversation_pair_id']}"
            )
        except Exception as e:
            # Log error but don't fail the streaming
            logger.error(f"[RETRY] Error archiving conversation: {e}", exc_info=True)

    return create_sse_response(event_stream())


@router.post("/react")
async def react(
    react_data: ReactRequest,
    request: Request,
    session_hash: str = Depends(get_session_hash),
):
    """
    Update reaction (like/dislike) for a specific message.

    Args:
        react_data: Request body with chatbot messages and reaction_json (Gradio format)
        request: FastAPI request for logging
        session_hash: Session identifier from X-Session-Hash header

    Returns:
        dict: Success status with reaction data

    Raises:
        HTTPException: If session not found
    """
    from backend.arena.session import (
        retrieve_session_conversations,
        update_session_conversations,
    )

    logger.info(
        f"[REACT] session={session_hash}, reaction={react_data.reaction_json}",
        extra={"request": request},
    )

    # Retrieve conversations
    try:
        conversations = Conversations.from_session(session_hash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Extract reaction index and data
    reaction_index = react_data.reaction_json.index
    reaction_bot = react_data.reaction_json.bot
    if reaction_index is None:
        raise HTTPException(status_code=400, detail="Missing reaction index")

    # Store reaction metadata on the corresponding message
    # The reaction index corresponds to the bot message
    # We need to find the assistant message at position (reaction_index * 2 + 1)
    conv = (
        conversations.conversation_a
        if reaction_bot == "a"
        else conversations.conversation_b
    )

    # FIXME try
    msg_index = reaction_index if not conv.has_system_msg else reaction_index + 1
    message = conv.messages[msg_index]
    message.reaction = react_data.reaction_json

    # Update in Redis
    conversations.store_to_session(session_hash)

    # Save reaction to database
    try:
        reaction_record = record_reaction(
            conversations=conversations,
            reaction=react_data.reaction_json,
            msg_index=msg_index,
            session_hash=session_hash,
            request=request,
        )
        logger.info(f"[REACT] Saved to database: {reaction_record}")
    except Exception as e:
        # Log error but don't fail the request
        logger.error(f"[REACT] Error saving to database: {e}", exc_info=True)

    return {
        "success": True,
        "index": reaction_index,
        "reaction": react_data.reaction_json,
    }


@router.post("/vote")
async def vote(
    request: Request,
    vote_data: VoteRequest,
    session_hash: str = Depends(get_session_hash),
):
    """
    Submit a vote after conversation and reveal model identities.

    Saves the vote to database and returns reveal data.

    Args:
        request: FastAPI request for logging
        vote_data: Request body with Gradio-format vote data
        session_hash: Session identifier from X-Session-Hash header

    Returns:
        dict: Reveal data with model names, metadata, and environmental stats

    Raises:
        HTTPException: If session not found or database error
    """
    from backend.arena.session import retrieve_session_conversations
    from backend.config import settings

    logger.info(
        f"[VOTE] session={session_hash}, chosen={vote_data.which_model_radio_output}",
        extra={"request": request},
    )

    # Retrieve conversations
    try:
        conv_a_dict, conv_b_dict, metadata = retrieve_session_conversations(
            session_hash
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Get IP for logging
    ip = get_ip(request)

    # Save vote to database with all preferences
    try:
        vote_record = record_vote(
            conversations=Conversations(
                conversation_a=deserialize_conversation_from_redis(conv_a_dict),
                conversation_b=deserialize_conversation_from_redis(conv_b_dict),
            ),
            vote_data=vote_data,
            request=request,
            mode=metadata.get("mode"),
            category=metadata.get("category"),
        )
        logger.info(f"[VOTE] Saved to database: {vote_record['conversation_pair_id']}")
    except Exception as e:
        # Log error but don't fail the request
        logger.error(f"[VOTE] Error saving to database: {e}", exc_info=True)

    # Build reveal data with environmental impact
    from backend.arena.reveal import build_reveal_dict

    reveal_data = build_reveal_dict(
        conv_a_dict, conv_b_dict, vote_data.which_model_radio_output
    )

    return reveal_data


@router.get("/reveal/{session_hash}")
async def reveal(session_hash: str, request: Request):
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

    # Build reveal data with environmental impact
    from backend.arena.reveal import build_reveal_dict

    # No chosen model for direct reveal (user just wants to see models without voting)
    reveal_data = build_reveal_dict(conversations, "both-equal")

    return reveal_data
