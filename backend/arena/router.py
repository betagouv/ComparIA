import logging

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from backend.arena.models import ReactRequest, VoteRequest
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
    from backend.arena.session import create_session, store_session_conversations
    from backend.arena.streaming import create_sse_response, stream_both_responses
    from backend.arena.models import UserMessage, create_conversations
    from backend.arena.utils import serialize_conversation_for_redis

    logger.info("chose mode: " + args.mode, extra={"request": request})
    logger.info(
        "custom_models_selection: " + str(args.custom_models_selection),
        extra={"request": request},
    )

    # Select models
    models = get_models()
    model_a, model_b = models.pick_two(args.mode, args.custom_models_selection)

    logger.info(f"Selected models: {model_a} vs {model_b}", extra={"request": request})

    # Create new session
    session_hash = create_session()

    # Initialize conversations using Pydantic models
    conversations = create_conversations(model_a, model_b, args.prompt_value)

    # Serialize for Redis storage
    conv_a_dict = serialize_conversation_for_redis(conversations.conversation_a)
    conv_b_dict = serialize_conversation_for_redis(conversations.conversation_b)

    # Store in Redis
    store_session_conversations(session_hash, conv_a_dict, conv_b_dict)

    # Stream responses
    async def event_stream():
        # Send session hash first
        import json

        yield f"data: {json.dumps({'type': 'init', 'session_hash': session_hash})}\n\n"

        # Stream both model responses
        async for chunk in stream_both_responses(conv_a_dict, conv_b_dict, request):
            yield chunk

    return create_sse_response(event_stream())


@router.post("/add_text", dependencies=[Depends(assert_not_rate_limited)])
async def add_text(
    args: "AddTextRequest",
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
    from backend.arena.models import AddTextRequest, UserMessage
    from backend.arena.session import (
        retrieve_session_conversations,
        update_session_conversations,
    )
    from backend.arena.streaming import create_sse_response, stream_both_responses

    logger.info(
        f"[ADD_TEXT] session={session_hash}, message_len={len(args.message)}",
        extra={"request": request},
    )

    # Retrieve conversations from Redis
    try:
        conv_a_dict, conv_b_dict = retrieve_session_conversations(session_hash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Add user message to both conversations
    user_message = UserMessage(content=args.message)
    conv_a_dict["messages"].append(user_message.model_dump())
    conv_b_dict["messages"].append(user_message.model_dump())

    # Update in Redis
    update_session_conversations(session_hash, conv_a_dict, conv_b_dict)

    # Stream responses
    async def event_stream():
        async for chunk in stream_both_responses(conv_a_dict, conv_b_dict, request):
            yield chunk

    return create_sse_response(event_stream())


@router.post("/retry", dependencies=[Depends(assert_not_rate_limited)])
async def retry(
    args: "RetryRequest",
    request: Request,
    session_hash: str = Depends(get_session_hash),
):
    """
    Retry generating the last bot response.

    Removes the last assistant messages and re-generates them.

    Args:
        args: Request body (currently empty, just needs session_hash)
        request: FastAPI request for logging
        session_hash: Session identifier from X-Session-Hash header

    Returns:
        StreamingResponse: SSE stream with new model responses

    Raises:
        HTTPException: If session not found or rate limiting triggered
    """
    from backend.arena.models import RetryRequest
    from backend.arena.session import (
        retrieve_session_conversations,
        update_session_conversations,
    )
    from backend.arena.streaming import create_sse_response, stream_both_responses

    logger.info(f"[RETRY] session={session_hash}", extra={"request": request})

    # Retrieve conversations
    try:
        conv_a_dict, conv_b_dict = retrieve_session_conversations(session_hash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Remove last assistant messages
    conv_a_dict["messages"] = [
        msg for msg in conv_a_dict["messages"] if msg.get("role") != "assistant"
    ]
    conv_b_dict["messages"] = [
        msg for msg in conv_b_dict["messages"] if msg.get("role") != "assistant"
    ]

    # Update in Redis
    update_session_conversations(session_hash, conv_a_dict, conv_b_dict)

    # Re-stream responses
    async def event_stream():
        async for chunk in stream_both_responses(conv_a_dict, conv_b_dict, request):
            yield chunk

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
        conv_a_dict, conv_b_dict = retrieve_session_conversations(session_hash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Extract reaction index and data
    reaction_index = react_data.reaction_json.get("index")
    if reaction_index is None:
        raise HTTPException(status_code=400, detail="Missing reaction index")

    # Store reaction metadata on the corresponding message
    # The reaction index corresponds to the bot message pair (0-indexed)
    # We need to find the assistant message at position (reaction_index * 2 + 1)
    message_position = (
        reaction_index * 2 + 1
    )  # User messages at even positions, assistant at odd

    # Update reaction in both conversations' messages
    for conv_dict in [conv_a_dict, conv_b_dict]:
        messages = conv_dict.get("messages", [])
        if message_position < len(messages):
            msg = messages[message_position]
            # Add reaction metadata to the message
            if isinstance(msg, dict):
                if "metadata" not in msg:
                    msg["metadata"] = {}
                msg["metadata"]["reaction"] = react_data.reaction_json
            else:
                # Handle ChatMessage object
                if not hasattr(msg, "metadata") or msg.metadata is None:
                    msg.metadata = {}
                msg.metadata["reaction"] = react_data.reaction_json

    # Update in Redis
    update_session_conversations(session_hash, conv_a_dict, conv_b_dict)

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
        conv_a_dict, conv_b_dict = retrieve_session_conversations(session_hash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Get IP for logging
    ip = get_ip(request)

    # TODO: Save vote to database with all preferences
    # For now just log the vote
    logger.info(
        f"[VOTE] Would save vote: chosen={vote_data.which_model_radio_output}, positive_a={vote_data.positive_a_output}, positive_b={vote_data.positive_b_output}"
    )

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
    from backend.arena.session import retrieve_session_conversations

    logger.info(f"[REVEAL] session={session_hash}", extra={"request": request})

    # Retrieve conversations
    try:
        conv_a_dict, conv_b_dict = retrieve_session_conversations(session_hash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Build reveal data with environmental impact
    from backend.arena.reveal import build_reveal_dict

    # No chosen model for direct reveal (user just wants to see models without voting)
    reveal_data = build_reveal_dict(conv_a_dict, conv_b_dict, "both-equal")

    return reveal_data
