"""
Module for handling conversations with AI models.

This module manages the interaction with multiple AI models through LiteLLM,
handling streaming responses, token counting, and message tracking.
"""

import gradio as gr

from languia.litellm import litellm_stream_iter
from litellm.litellm_core_utils.token_counter import token_counter

import time
from languia.custom_components.customchatbot import (
    ChatMessage,
)

from languia.utils import EmptyResponseError, messages_to_dict_list, get_api_key
from languia import config

import logging

from uuid import uuid4

from backend.models.data import models


class Conversation:
    """
    Represents a conversation with a single AI model.

    Stores messages, model information, and metadata about the conversation.
    Each conversation has a unique ID and tracks the model's endpoint for API calls.
    """

    def __init__(
        self,
        messages=[],
        model_name=None,
    ):
        """
        Initialize a conversation with an optional system prompt.

        Args:
            messages: List of ChatMessage objects for this conversation
            model_name: Name of the model to use for this conversation
        """
        # Load model-specific system prompt (e.g., French instructions)
        system_prompt = config.get_model_system_prompt(model_name)
        if system_prompt:
            # Prepend system prompt to messages if available
            self.messages = [
                ChatMessage(role="system", content=system_prompt)
            ] + messages
        else:
            self.messages = messages
        # Generate unique conversation ID without hyphens
        self.conv_id = str(uuid4()).replace("-", "")
        self.model_name = model_name
        # Retrieve API endpoint configuration for this model
        self.endpoint = models.get(model_name, {}).get("endpoint", {})


logger = logging.getLogger("languia")


def update_last_message(
    messages,
    text,
    position,
    output_tokens=None,
    generation_id=None,
    duration=0,
    reasoning=None,
):
    """
    Update or create the last message in a conversation with model response data.

    This function handles streaming responses by creating or updating the bot's message
    with partial text, token counts, reasoning, and performance metrics.

    Args:
        messages: List of ChatMessage objects
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
    if not messages or messages[-1].role == "user":
        return messages + [
            ChatMessage(
                role="assistant", content=text, metadata=metadata, reasoning=reasoning
            )
        ]

    # Update existing message with streaming chunks
    last_message = messages[-1]
    last_message.content = text
    last_message.metadata = {**last_message.metadata, **metadata}
    if reasoning is not None:
        last_message.reasoning = reasoning

    return messages


def bot_response(
    position,
    state,
    request: gr.Request,
    temperature=0.7,
    # top_p=1.0,
    max_new_tokens=4096,
):
    """
    Stream a response from an AI model.

    This is a generator function that yields conversation state updates as the model
    generates responses token by token. It handles model endpoint configuration,
    API calls through LiteLLM, token counting, and performance tracking.

    Args:
        position: Which model position ("a" or "b") to respond
        state: Conversation object with messages and model info
        request: Gradio request context for logging
        temperature: Sampling temperature (default 0.7)
        max_new_tokens: Maximum tokens to generate (default 4096)

    Yields:
        Updated conversation state as response chunks arrive

    Raises:
        Exception: If model endpoint is not configured
        EmptyResponseError: If model returns empty response
    """
    # Note: temperature and top_p can be converted to float/int if needed

    # Validate that the model has a configured endpoint
    if not state.endpoint:
        logger.critical(
            "No endpoint for model name: " + str(state.model_name),
            extra={"request": request},
        )
        raise Exception("No endpoint for model name: " + str(state.model_name))

    endpoint = state.endpoint

    # Get endpoint identifier for logging (API provider name)
    endpoint_name = endpoint.get("api_id", state.model_name)
    logger.info(
        f"using endpoint {endpoint_name} for {state.model_name}",
        extra={"request": request},
    )
    # Check if this model supports extended reasoning (like o1)
    include_reasoning = endpoint.get("include_reasoning", True)

    # Track generation start time for performance metrics
    start_tstamp = time.time()

    # Convert ChatMessage objects to dict format for API calls
    messages_dict = messages_to_dict_list(state.messages)
    # Build LiteLLM model identifier (e.g., "openai/gpt-4", "google/gemini-pro")
    litellm_model_name = (
        endpoint.get("api_type", "openai")
        + "/"
        + endpoint.get("api_model_id", state.model_name)
    )

    # Retrieve API key from environment or config
    api_key = get_api_key(endpoint)

    # Initialize streaming iterator from LiteLLM
    stream_iter = litellm_stream_iter(
        model_name=litellm_model_name,
        messages=messages_dict,
        temperature=temperature,
        api_key=api_key,
        api_base=endpoint.get("api_base", None),
        api_version=endpoint.get("api_version", None),
        max_new_tokens=max_new_tokens,
        request=request,
        vertex_ai_location=endpoint.get("vertex_ai_location", None),
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
            # Update conversation state with partial response
            state.messages = update_last_message(
                messages=state.messages,
                text=output,
                position=position,
                output_tokens=output_tokens,
                generation_id=generation_id,
                reasoning=reasoning,
            )
            # Yield to frontend for real-time display
            yield (state)

    # Log generation ID for API debugging
    if generation_id:
        logger.info(
            f"generation_id: {generation_id} for {litellm_model_name}",
            extra={"request": request},
        )

    # Calculate total generation duration
    stop_tstamp = time.time()
    duration = stop_tstamp - start_tstamp
    logger.debug(
        f"duration for {generation_id}: {str(duration)}", extra={"request": request}
    )

    # Extract final response text and reasoning from last chunk
    output = data.get("text")
    reasoning = data.get("reasoning")
    # Check for empty responses and raise error
    if (not output or output == "") and (not reasoning or reasoning == ""):
        logger.error(
            f"reponse_vide: {state.model_name}, data: " + str(data),
            exc_info=True,
            extra={"request": request},
        )
        raise EmptyResponseError(
            f"No answer from API {endpoint_name} for model {state.model_name}"
        )

    # Fallback: count tokens locally if API didn't provide them
    if not output_tokens:
        output_tokens = token_counter(text=[reasoning, output], model=state.model_name)

    # Final update with complete response and timing data
    state.messages = update_last_message(
        messages=state.messages,
        text=output,
        position=position,
        output_tokens=output_tokens,
        duration=duration,
        reasoning=reasoning,
    )

    # Final yield with complete response
    yield (state)
