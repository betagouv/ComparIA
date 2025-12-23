import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

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


@router.post("/init")
async def init_arena(request: Request) -> dict:
    """
    Initialize a new arena session.

    Returns:
        dict: Session hash and available models
    """
    from backend.arena.session import create_session

    session_hash = create_session()
    models = get_models()

    return {
        "session_hash": session_hash,
        "available_models": {k: v.model_dump() for k, v in models.enabled.items()},
        "data_timestamp": models.data_timestamp,
    }


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
    from languia.conversation import Conversation
    from languia.custom_components.customchatbot import ChatMessage

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

    # Initialize conversations
    user_message = ChatMessage(role="user", content=args.prompt_value)

    conv_a = Conversation(messages=[user_message], model_name=model_a)
    conv_b = Conversation(messages=[user_message], model_name=model_b)

    # Convert to dicts for Redis storage
    conv_a_dict = {
        "messages": conv_a.messages,
        "model_name": conv_a.model_name,
        "endpoint": conv_a.endpoint,
        "conv_id": conv_a.conv_id,
    }
    conv_b_dict = {
        "messages": conv_b.messages,
        "model_name": conv_b.model_name,
        "endpoint": conv_b.endpoint,
        "conv_id": conv_b.conv_id,
    }

    # Store in Redis
    store_session_conversations(session_hash, conv_a_dict, conv_b_dict)

    # Stream responses
    async def event_stream():
        # Send session hash first
        import json

        yield f'data: {json.dumps({"type": "init", "session_hash": session_hash})}\n\n'

        # Stream both model responses
        async for chunk in stream_both_responses(conv_a_dict, conv_b_dict, request):
            yield chunk

    return create_sse_response(event_stream())


@router.post("/add_text", dependencies=[Depends(assert_not_rate_limited)])
async def add_text(
    args: "AddTextRequest", request: Request, session_hash: str = Depends(get_session_hash)
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
    from backend.arena.models import AddTextRequest
    from backend.arena.session import retrieve_session_conversations, update_session_conversations
    from backend.arena.streaming import create_sse_response, stream_both_responses
    from languia.custom_components.customchatbot import ChatMessage

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
    user_message = ChatMessage(role="user", content=args.message)
    conv_a_dict["messages"].append(user_message)
    conv_b_dict["messages"].append(user_message)

    # Update in Redis
    update_session_conversations(session_hash, conv_a_dict, conv_b_dict)

    # Stream responses
    async def event_stream():
        async for chunk in stream_both_responses(conv_a_dict, conv_b_dict, request):
            yield chunk

    return create_sse_response(event_stream())


@router.post("/retry", dependencies=[Depends(assert_not_rate_limited)])
async def retry(
    args: "RetryRequest", request: Request, session_hash: str = Depends(get_session_hash)
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
    from backend.arena.session import retrieve_session_conversations, update_session_conversations
    from backend.arena.streaming import create_sse_response, stream_both_responses

    logger.info(f"[RETRY] session={session_hash}", extra={"request": request})

    # Retrieve conversations
    try:
        conv_a_dict, conv_b_dict = retrieve_session_conversations(session_hash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Remove last assistant messages
    conv_a_dict["messages"] = [
        msg for msg in conv_a_dict["messages"] if msg.role != "assistant"
    ]
    conv_b_dict["messages"] = [
        msg for msg in conv_b_dict["messages"] if msg.role != "assistant"
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
    args: "ReactRequest", request: Request, session_hash: str = Depends(get_session_hash)
):
    """
    Update reaction (like/dislike) for a specific message.

    Args:
        args: Request body with message_id and reaction
        request: FastAPI request for logging
        session_hash: Session identifier from X-Session-Hash header

    Returns:
        dict: Success status

    Raises:
        HTTPException: If session or message not found
    """
    from backend.arena.models import ReactRequest
    from backend.arena.session import retrieve_session_conversations, update_session_conversations

    logger.info(
        f"[REACT] session={session_hash}, message_id={args.message_id}, reaction={args.reaction}",
        extra={"request": request},
    )

    # Retrieve conversations
    try:
        conv_a_dict, conv_b_dict = retrieve_session_conversations(session_hash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Find and update message reaction
    message_found = False
    for conv_dict in [conv_a_dict, conv_b_dict]:
        for msg in conv_dict["messages"]:
            # Check if message has matching ID (may need to add ID field to ChatMessage)
            if hasattr(msg, "id") and msg.id == args.message_id:
                msg.reaction = args.reaction
                message_found = True
                break
        if message_found:
            break

    if not message_found:
        raise HTTPException(status_code=404, detail=f"Message {args.message_id} not found")

    # Update in Redis
    update_session_conversations(session_hash, conv_a_dict, conv_b_dict)

    return {"success": True, "message_id": args.message_id, "reaction": args.reaction}


@router.post("/vote")
async def vote(
    args: "VoteRequest", request: Request, session_hash: str = Depends(get_session_hash)
):
    """
    Submit a vote after conversation and reveal model identities.

    Saves the vote to database and returns reveal data.

    Args:
        args: Request body with chosen_model, preferences, and optional comment
        request: FastAPI request for logging
        session_hash: Session identifier from X-Session-Hash header

    Returns:
        dict: Success status and reveal data

    Raises:
        HTTPException: If session not found or database error
    """
    from backend.arena.models import VoteRequest
    from backend.arena.session import retrieve_session_conversations
    from languia.logs import save_vote_to_db

    logger.info(
        f"[VOTE] session={session_hash}, chosen={args.chosen_model}",
        extra={"request": request},
    )

    # Retrieve conversations
    try:
        conv_a_dict, conv_b_dict = retrieve_session_conversations(session_hash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Get IP for logging
    ip = get_ip(request)

    # Prepare vote data
    vote_data = {
        "session_hash": session_hash,
        "chosen_model": args.chosen_model,
        "model_a": conv_a_dict["model_name"],
        "model_b": conv_b_dict["model_name"],
        "conversation_a": [
            {"role": msg.role, "content": msg.content} for msg in conv_a_dict["messages"]
        ],
        "conversation_b": [
            {"role": msg.role, "content": msg.content} for msg in conv_b_dict["messages"]
        ],
        "preferences": args.preferences,
        "comment": args.comment,
        "ip": ip,
    }

    # Save to database
    try:
        save_vote_to_db(vote_data)
    except Exception as e:
        logger.error(f"[VOTE] Error saving vote: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save vote")

    # Get model metadata for reveal
    models = get_models()
    model_a_metadata = models.all.get(conv_a_dict["model_name"], {})
    model_b_metadata = models.all.get(conv_b_dict["model_name"], {})

    reveal_data = {
        "model_a": conv_a_dict["model_name"],
        "model_b": conv_b_dict["model_name"],
        "model_a_metadata": model_a_metadata.model_dump() if hasattr(model_a_metadata, "model_dump") else model_a_metadata,
        "model_b_metadata": model_b_metadata.model_dump() if hasattr(model_b_metadata, "model_dump") else model_b_metadata,
    }

    return {"success": True, "reveal": reveal_data}


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

    # Get model metadata
    models = get_models()
    model_a_metadata = models.all.get(conv_a_dict["model_name"], {})
    model_b_metadata = models.all.get(conv_b_dict["model_name"], {})

    return {
        "model_a": conv_a_dict["model_name"],
        "model_b": conv_b_dict["model_name"],
        "model_a_metadata": model_a_metadata.model_dump() if hasattr(model_a_metadata, "model_dump") else model_a_metadata,
        "model_b_metadata": model_b_metadata.model_dump() if hasattr(model_b_metadata, "model_dump") else model_b_metadata,
    }
