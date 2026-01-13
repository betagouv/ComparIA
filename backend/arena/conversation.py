"""
Module for handling conversations with AI models.

This module manages the interaction with multiple AI models through LiteLLM,
handling streaming responses, token counting, and message tracking.

Uses Pydantic Conversation model update and validation during streaming.
"""

import logging
import time

from litellm.litellm_core_utils.token_counter import token_counter

from backend.arena.litellm import get_api_key, litellm_stream_iter
from backend.arena.models import (
    AnyMessage,
    AssistantMessage,
    Conversation,
    SystemMessage,
    UserMessage,
)
from backend.errors import EmptyResponseError

logger = logging.getLogger("languia")


def update_last_message(
    messages: list[AnyMessage],
    text,
    position,
    output_tokens=None,
    generation_id=None,
    duration=0,
    reasoning=None,
) -> list[AnyMessage]:
    """
    Update or create the last message in a conversation with model response data.

    This function handles streaming responses by creating or updating the bot's message
    with partial text, token counts, reasoning, and performance metrics.

    Args:
        messages: List of AnyMessage objects
        text: The response text to add/update
        position: Which model ("a" or "b") generated this response
        output_tokens: Number of tokens in the response
        generation_id: Unique ID for this generation (from API)
        duration: Time taken to generate the response
        reasoning: Extended thinking/reasoning content (for models like o1)

    Returns:
        Updated messages list
    """
    # Create metadata dictionary with optional fields
    metadata = {
        "bot": position,
        **({"output_tokens": output_tokens} if output_tokens else {}),
        **({"generation_id": generation_id} if generation_id else {}),
        **({"duration": duration} if duration != 0 else {}),
    }

    # Create new message if the last message is from user or list is empty
    if not isinstance(messages[-1], AssistantMessage):
        messages.append(
            AssistantMessage(content=text, metadata=metadata, reasoning=reasoning)
        )
        return messages

    # Update existing message with streaming chunks
    last_message = messages[-1]
    last_message.content = text
    last_message.metadata = {**last_message.metadata.model_dump(), **metadata}
    if reasoning is not None:
        last_message.reasoning = reasoning

    return messages


async def bot_response_async(
    position,
    state: Conversation,
    ip: str,
    temperature=0.7,
    max_new_tokens=4096,
):
    """
    Stream a response from an AI model asynchronously.

    This is an async generator function that yields conversation state updates as the model
    generates responses token by token.

    Args:
        position: Which model position ("a" or "b") to respond
        state: Conversation (Pydantic model) with messages and model info
        ip: Client IP address for logging
        temperature: Sampling temperature (default 0.7)
        max_new_tokens: Maximum tokens to generate (default 4096)

    Yields:
        Updated Conversation (Pydantic) as response chunks arrive

    Raises:
        Exception: If model endpoint is not configured
        EmptyResponseError: If model returns empty response
    """
    # Validate that the model has a configured endpoint
    if not state.endpoint:
        logger.critical(
            f"No endpoint for model: {state.model_name}",
            extra={"ip": ip},
        )
        raise Exception(f"No endpoint for model: {state.model_name}")

    endpoint = state.endpoint

    # Get endpoint identifier for logging (API provider name)
    endpoint_name = endpoint.api_id if hasattr(endpoint, "api_id") else state.model_name
    logger.info(
        f"using endpoint {endpoint_name} for {state.model_name}",
        extra={"ip": ip},
    )
    # Check if this model supports extended reasoning (like o1)
    include_reasoning = (
        endpoint.include_reasoning if hasattr(endpoint, "include_reasoning") else True
    )

    # Track generation start time for performance metrics
    start_tstamp = time.time()

    # Build LiteLLM model identifier (e.g., "openai/gpt-4", "google/gemini-pro")
    api_type = endpoint.api_type if hasattr(endpoint, "api_type") else "openai"
    api_model_id = (
        endpoint.api_model_id if hasattr(endpoint, "api_model_id") else state.model_name
    )
    litellm_model_name = f"{api_type}/{api_model_id}"

    # Retrieve API key from environment or config
    api_key = get_api_key(endpoint)

    # Get optional endpoint attributes
    api_base = endpoint.api_base if hasattr(endpoint, "api_base") else None
    api_version = endpoint.api_version if hasattr(endpoint, "api_version") else None
    vertex_ai_location = (
        endpoint.vertex_ai_location if hasattr(endpoint, "vertex_ai_location") else None
    )

    # Initialize streaming iterator from LiteLLM
    stream_iter = litellm_stream_iter(
        model_name=litellm_model_name,
        messages=[
            msg.model_dump(include={"role", "content"}) for msg in state.messages
        ],  # Only pass supported message args 'role' and 'content'
        temperature=temperature,
        api_key=api_key,
        api_base=api_base,
        api_version=api_version,
        max_new_tokens=max_new_tokens,
        ip=ip,
        vertex_ai_location=vertex_ai_location,
        include_reasoning=include_reasoning,
    )

    output_tokens = None
    generation_id = None

    # Process streaming response chunks
    for data in stream_iter:
        # Extract token count from API response if available
        if "output_tokens" in data:
            output_tokens = data["output_tokens"]
        # Extract generation ID for tracking (used by some APIs)
        if "generation_id" in data:
            generation_id = data["generation_id"]

        # Get response text and reasoning (for reasoning models)
        output = data.get("text")
        reasoning = data.get("reasoning")
        # Yield intermediate results only if there's content to display
        if output or reasoning:
            output.strip()
            # Update messages with partial response
            update_last_message(
                messages=state.messages,
                text=output,
                position=position,
                output_tokens=output_tokens,
                generation_id=generation_id,
                reasoning=reasoning,
            )
            yield state

    # Log generation ID for API debugging
    if generation_id:
        logger.info(
            f"generation_id: {generation_id} for {litellm_model_name}",
            extra={"ip": ip},
        )

    # Calculate total generation duration
    stop_tstamp = time.time()
    duration = stop_tstamp - start_tstamp
    logger.debug(f"duration for {generation_id}: {str(duration)}", extra={"ip": ip})

    # Extract final response text and reasoning from last chunk
    output = data.get("text")
    reasoning = data.get("reasoning")
    # Check for empty responses and raise error
    if (not output or output == "") and (not reasoning or reasoning == ""):
        logger.error(
            f"reponse_vide: {state.model_name}, data: {str(data)}",
            exc_info=True,
            extra={"ip": ip},
        )
        raise EmptyResponseError(
            f"No answer from API {endpoint_name} for model {state.model_name}"
        )

    # Fallback: count tokens locally if API didn't provide them
    if not output_tokens:
        output_tokens = token_counter(text=[reasoning, output], model=state.model_name)

    # Final update with complete response and timing data
    update_last_message(
        messages=state.messages,
        text=output,
        position=position,
        output_tokens=output_tokens,
        duration=duration,
        reasoning=reasoning,
    )

    yield state
