"""
Module for handling conversations with AI models.

This module manages the interaction with multiple AI models through LiteLLM,
handling streaming responses, token counting, and message tracking.

Uses Pydantic Conversation model update and validation during streaming.
"""

import logging
import time
from typing import AsyncGenerator

from fastapi import Request
from litellm.litellm_core_utils.token_counter import token_counter

from backend.arena.litellm import litellm_stream_iter
from backend.arena.models import (
    AnyMessage,
    AssistantMessage,
    AssistantMessageMetadata,
    Conversation,
)
from backend.errors import EmptyResponseError

logger = logging.getLogger("languia")


async def bot_response_async(
    position,
    state: Conversation,
    request: Request,
    temperature=0.7,
    max_new_tokens=4096,
) -> AsyncGenerator[list[AnyMessage]]:
    """
    Stream a response from an AI model asynchronously.

    This is an async generator function that yields conversation state updates as the model
    generates responses token by token.

    Args:
        position: Which model position ("a" or "b") to respond
        state: Conversation (Pydantic model) with messages and model info
        request: FastAPI request for logging
        temperature: Sampling temperature (default 0.7)
        max_new_tokens: Maximum tokens to generate (default 4096)

    Yields:
        Updated message list as response chunks arrive

    Raises:
        EmptyResponseError: If model returns empty response
    """
    # Add new partial AssistantMessage to chat
    metadata = AssistantMessageMetadata(generation_id="", bot=position)
    current_msg = AssistantMessage(metadata=metadata)
    state.messages.append(current_msg)

    # Track generation start time for performance metrics
    start_tstamp = time.time()

    # Initialize streaming iterator from LiteLLM
    stream_iter = litellm_stream_iter(
        model_name=state.model_name,
        endpoint=state.llm.endpoint,
        messages=state.messages,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        request=request,
    )

    # Process streaming response chunks and update current message
    for data in stream_iter:
        if not current_msg.metadata.generation_id:
            current_msg.metadata.generation_id = data["generation_id"]
        if data["output_tokens"]:
            current_msg.metadata.output_tokens = data["output_tokens"]

        if data["content"] or data["reasoning"]:
            current_msg.content = data["content"].strip()
            current_msg.reasoning = data["reasoning"].strip()

        # Yield complete chat only if there's content to display in current message
        if current_msg.content or current_msg.reasoning:
            yield state.messages

    # Calculate total generation duration
    stop_tstamp = time.time()
    current_msg.metadata.duration = stop_tstamp - start_tstamp
    logger.debug(
        f"duration for {data["generation_id"]}: {current_msg.metadata.duration}",
        extra={"request": request},
    )

    # Check for empty responses and raise error (check on data that is not stripped)
    if not data["content"] and not data["reasoning"]:
        logger.error(
            f"reponse_vide: {state.model_name}, message: {current_msg}",
            exc_info=True,
            extra={"request": request},
        )
        raise EmptyResponseError(
            f"No answer from API '{state.llm.endpoint.api_model_id}' for model '{state.model_name}'"
        )

    # Fallback: count tokens locally if API didn't provide them
    if not current_msg.metadata.output_tokens:
        current_msg.metadata.output_tokens = token_counter(
            text=[data["reasoning"], data["content"]],
            model=state.model_name,
        )

    # Final update with complete response and timing data
    yield state.messages
