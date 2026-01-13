import logging
from typing import Annotated, TypedDict

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.arena.models import (
    AddFirstTextBody,
    AddTextBody,
    AssistantMessage,
    Conversations,
    ReactionBody,
    ReactionData,
    RevealData,
    UserMessage,
    VoteBody,
    create_conversations,
)
from backend.arena.persistence import (
    delete_reaction,
    record_conversations,
    record_reaction,
    record_vote,
)
from backend.arena.reveal import get_chosen_llm, get_reveal_data
from backend.arena.session import (
    create_session,
    is_ratelimited,
    retrieve_session_conversations,
    store_session_conversations,
    update_session_conversations,
)
from backend.arena.streaming import create_sse_response, stream_both_responses
from backend.language_models.data import get_models
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
            detail="Vous avez trop sollicité les modèles parmi les plus onéreux, veuillez réessayer dans quelques heures. Vous pouvez toujours solliciter des modèles plus petits.",
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
    reaction_body: ReactionBody,
    conversations: ConversationsAnno,
    request: Request,
) -> ReactReturnType:
    """
    Update reaction (like/dislike) for a specific message.

    Args:
        reaction_body: Request body with reaction data
        conversations: Conversations from session_hash
        request: FastAPI request for logging

    Returns:
        dict: reaction data

    Raises:
        HTTPException: If session not found
    """

    logger.info(
        f"[REACT] session={conversations.session_hash}, reaction={reaction_body.model_dump()}",
        extra={"request": request},
    )

    conv = (
        conversations.conversation_a
        if reaction_body.bot == "a"
        else conversations.conversation_b
    )

    # Get real message index from front which is the message index without counting system message
    msg_index = (
        reaction_body.index if not conv.has_system_msg else reaction_body.index + 1
    )
    message = conv.messages[msg_index] if len(conv.messages) > msg_index else None

    if not message or not isinstance(message, AssistantMessage):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assistant message not found"
        )

    if reaction_body.liked is None:
        # A reaction has been undone, remove it from its message and db
        message.reaction = None
        # Store conversations with removed reaction
        conversations.store_to_session()
        # Delete db reaction
        delete_reaction(conv, msg_index)

        return {"reaction": None}

    # Build final reaction data
    # FIXME replace reaction.index with msg_index?
    reaction = ReactionData.model_validate(reaction_body, from_attributes=True)

    message.reaction = reaction
    # Store conversations with updated reaction to redis
    conversations.store_to_session()
    # Store reaction to db/logs
    reaction_record = record_reaction(
        conversations=conversations,
        reaction=reaction,
        msg_index=msg_index,
        chatbot_index=reaction_body.index,
        request=request,
    )

    return {"reaction": reaction}


@router.post("/vote")
async def vote(
    vote_body: VoteBody,
    conversations: ConversationsAnno,
    request: Request,
) -> RevealData:
    """
    Submit a vote after conversation and reveal model identities.

    Saves the vote to database and returns reveal data.

    Args:
        vote_body: Request body with vote data
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
        f"[VOTE] session={conversations.session_hash}, chosen={vote_body.chosen_llm}",
        extra={"request": request},
    )

    # FIXME not sure it is usefull to save vote to Conversations
    conversations.vote = vote_body
    # Store conversations with updated vote to redis
    conversations.store_to_session()

    # Save vote to database with prefs and comments
    record_vote(
        conversations=conversations,
        vote=vote_body,
        request=request,
    )

    # Return computed reveal data with environmental impact
    return get_reveal_data(conversations, vote_body.chosen_llm)


@router.get("/reveal")
async def reveal(conversations: ConversationsAnno, request: Request) -> RevealData:
    """
    Get reveal data for a session (model identities and metadata).

    Args:
        conversations: Conversations from session_hash
        request: FastAPI request for logging

    Returns:
        dict: Reveal data with model names and metadata

    Raises:
        HTTPException: If session not found
    """
    logger.info(
        f"[REVEAL] session={conversations.session_hash}", extra={"request": request}
    )

    chosen_llm = get_chosen_llm(conversations)

    if chosen_llm is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No reaction or vote found, can't access reveal",
        )

    # Return computed reveal data with environmental impact
    return get_reveal_data(conversations, chosen_llm)
