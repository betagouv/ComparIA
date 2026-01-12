"""
Utility functions for ComparIA backend.

This module provides helper functions for:
- Model parameter calculations (total and active parameters)
- User/request information extraction (IP, Matomo tracking)
- Message and conversation utilities
- Model selection and picking logic
- Data transformation for API calls and storage
"""

import logging
import os

from backend.arena.models import AnyMessage, AssistantMessage
from backend.utils.user import get_ip

logger = logging.getLogger("languia")


class ContextTooLongError(ValueError):
    """Raised when the context window of a model is exceeded."""

    def __str__(self):
        return "Context too long."


class EmptyResponseError(RuntimeError):
    """Raised when a model API returns an empty response."""

    def __init__(self, response=None, *args: object) -> None:
        super().__init__(*args)
        self.response = response

    def __str__(self):
        msg = "Empty response"
        return msg


def get_chosen_model(which_model_radio):
    """
    Extract model choice from radio button value.

    Args:
        which_model_radio: Radio button value ("model-a", "model-b", or other)

    Returns:
        str: "model-a" or "model-b", or None if neither selected
    """
    if which_model_radio in ["model-a", "model-b"]:
        chosen_model = which_model_radio
    else:
        chosen_model = None
    return chosen_model


def get_chosen_model_name(which_model_radio, conversations):
    """
    Get the actual model name from the chosen option.

    Args:
        which_model_radio: Choice indicator ("model-a", "model-b", or other)
        conversations: Tuple of two Conversation objects (model A and B)

    Returns:
        str: Model name, or None if "both equal" or other option
    """
    if which_model_radio == "model-a":
        chosen_model_name = conversations[0].model_name
    elif which_model_radio == "model-b":
        chosen_model_name = conversations[1].model_name
    else:
        chosen_model_name = None
    return chosen_model_name


def count_turns(messages):
    """
    Count the number of conversation turns (user messages or exchanges).

    A turn is one user message and one bot response pair.

    Args:
        messages: List of ChatMessage objects

    Returns:
        int: Number of turns (exchanges between user and bot)
    """
    # If first message is system prompt, skip it in count
    if messages[0].role == "system":
        return (len(messages) - 1) // 2
    else:
        return len(messages) // 2


def is_unedited_prompt(opening_msg, category):
    """
    Check if the user's opening message is from a suggested prompt.

    Used to identify whether the user wrote custom text or used a predefined prompt.

    Args:
        opening_msg: User's first message content
        category: Selected prompt category (e.g., 'writing', 'coding')

    Returns:
        bool: True if message matches a suggested prompt, False otherwise
    """
    if not category:
        return False
    from backend.config import prompts_table

    # Check if the exact message exists in the category's prompt list
    return opening_msg in prompts_table[category]


def metadata_to_dict(metadata):
    """
    Clean and filter message metadata for storage/transmission.

    Removes system fields (bot position) and empty fields (duration=0, missing generation_id).

    Args:
        metadata: Dict of message metadata (tokens, generation_id, duration, etc.)

    Returns:
        dict: Filtered metadata, or None if empty
    """
    if not metadata:
        return None
    metadata_dict = dict(metadata)
    # Remove internal "bot" field used for tracking which model generated message
    metadata_dict.pop("bot", None)
    # Remove duration if not set or zero
    if not metadata_dict.get("duration") or metadata_dict.get("duration") == 0:
        metadata_dict.pop("duration", None)
    # Remove generation_id if not set
    if not metadata_dict.get("generation_id"):
        metadata_dict.pop("generation_id", None)
    return metadata_dict if metadata_dict else None


def strip_metadata(messages: list[dict]) -> list[dict]:
    """
    Remove all metadata from messages for API calls.

    API providers don't understand custom metadata fields, so we strip them before sending.

    Args:
        messages: List of message dicts with role/content/metadata

    Returns:
        list: Messages with only role and content fields
    """
    stripped_messages: list[dict] = []
    for message in messages:
        # Keep only role and content, drop metadata
        if "content" in message:
            stripped_messages.append(
                {"role": message["role"], "content": message["content"]}
            )
        else:
            # Handle missing content gracefully
            stripped_messages.append({"role": message["role"], "content": ""})
    return stripped_messages


def messages_to_dict_list(
    messages: list[AnyMessage],
    strip_metadata=False,
    concat_reasoning_with_content=False,
) -> list[dict]:
    """
    Convert ChatMessage objects to dict format for API calls or storage.

    Handles reasoning content (for reasoning models) and metadata serialization.

    Args:
        messages: List of ChatMessage objects
        strip_metadata: If True, don't include metadata in output
        concat_reasoning_with_content: If True, prepend reasoning to message content

    Returns:
        list: Messages as dicts with role, content, and optional reasoning/metadata
    """
    output = []
    for message in messages:
        msg_dict: dict = {"role": message.role}

        # Handle reasoning content (for o1 and similar models)
        if (
            isinstance(message, AssistantMessage)
            and message.reasoning
            and not concat_reasoning_with_content
        ):
            # Store reasoning separately if model supports it
            msg_dict["reasoning_content"] = message.reasoning
        elif (
            isinstance(message, AssistantMessage)
            and message.reasoning
            and concat_reasoning_with_content
        ):
            # Concatenate reasoning with content for models that don't support separate reasoning
            msg_dict["content"] = (
                "<|think|>" + message.reasoning + "<|think|>" + message.content
            )
        else:
            msg_dict["content"] = message.content

        # Include metadata if not stripped and not empty
        if (
            isinstance(message, AssistantMessage)
            and not strip_metadata
            and metadata_to_dict(message.metadata)
        ):
            msg_dict["metadata"] = metadata_to_dict(message.metadata)

        output.append(msg_dict)
    return output


def get_api_key(endpoint):
    """
    Get the appropriate API key for an endpoint.

    Different providers require different API keys:
    - Albert (French LLM): ALBERT_KEY
    - HuggingFace Inference: HF_INFERENCE_KEY
    - OpenRouter/Vertex: handled by LiteLLM from env variables

    Args:
        endpoint: Endpoint configuration dict with api_base

    Returns:
        str: API key, or None if using standard provider (OpenRouter/Vertex)
    """
    # Albert is French government LLM
    # "api_base": "https://albert.api.etalab.gouv.fr/v1/",

    # Handle both dict and Pydantic Endpoint object
    api_base = (
        endpoint.api_base if hasattr(endpoint, "api_base") else endpoint.get("api_base")
    )

    # "api_type": "huggingface/cohere" doesn't work, using the openai api type and api_base="https://router.huggingface.co/cohere/compatibility/v1/"
    if api_base and "albert.api.etalab.gouv.fr" in api_base:
        return os.getenv("ALBERT_KEY")
    # HuggingFace Inference API
    if api_base and "huggingface.co" in api_base:
        return os.getenv("HF_INFERENCE_KEY")
    # OpenRouter and Vertex AI are handled by LiteLLM reading env variables directly
    # OPENROUTER_API_KEY and Google credentials are checked automatically
    # Normally no need for OpenRouter, litellm reads OPENROUTER_API_KEY env value
    # And no need for Vertex, handled with GOOGLE_APPLICATION_CREDENTIALS pointing to a json file
    return None


def sum_tokens(messages) -> int:
    """
    Sum the total output tokens across all bot messages in a conversation.

    Args:
        messages: List of ChatMessage objects, AnyMessage objects, or dicts

    Returns:
        int: Total output tokens generated by the model
    """
    from backend.arena.models import AssistantMessage

    # Add up output_tokens from metadata of all assistant messages
    # Handle ChatMessage objects, AnyMessage types, and dicts
    total_output_tokens = 0
    for msg in messages:
        # Handle Pydantic AssistantMessage
        if isinstance(msg, AssistantMessage):
            total_output_tokens += msg.metadata.output_tokens
        # Handle dicts
        elif isinstance(msg, dict):
            if msg.get("role") == "assistant":
                tokens = msg.get("metadata", {}).get("output_tokens", 0)
                total_output_tokens += tokens or 0
        # Handle ChatMessage (has .role and .metadata attributes)
        elif hasattr(msg, "role") and msg.role == "assistant":
            tokens = msg.metadata.get("output_tokens", 0)
            total_output_tokens += tokens or 0

    return total_output_tokens
