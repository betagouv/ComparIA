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
