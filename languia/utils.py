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
from typing import TYPE_CHECKING

import gradio as gr
import numpy as np
from gradio import Request

if TYPE_CHECKING:
    from backend.models.models import Endpoint

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


def get_matomo_tracker_from_cookies(cookies):
    """
    Extract Matomo/Piwik visitor ID from cookies.

    Used for anonymous visitor tracking (if enabled by user).

    Args:
        cookies: Request cookies list (tuples of [key, value])

    Returns:
        str: Matomo visitor ID, or None if not found
    """
    logger = logging.getLogger("languia")
    # Matomo cookies start with "_pk_id."
    for cookie in cookies:
        if cookie[0].startswith("_pk_id."):
            logger.debug(f"Found matomo cookie: {cookie[0]}: {cookie[1]}")
            return cookie[1]
    return None


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
    from languia.config import prompts_table

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
    messages, strip_metadata=False, concat_reasoning_with_content=False
):
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
        msg_dict = {"role": message.role}

        # Handle reasoning content (for o1 and similar models)
        if message.reasoning and not concat_reasoning_with_content:
            # Store reasoning separately if model supports it
            msg_dict["reasoning_content"] = message.reasoning
        elif message.reasoning and concat_reasoning_with_content:
            # Concatenate reasoning with content for models that don't support separate reasoning
            msg_dict["content"] = (
                "<|think|>" + message.reasoning + "<|think|>" + message.content
            )
        else:
            msg_dict["content"] = message.content

        # Include metadata if not stripped and not empty
        if not strip_metadata and metadata_to_dict(message.metadata):
            msg_dict["metadata"] = metadata_to_dict(message.metadata)

        output.append(msg_dict)
    return output


def get_user_info(request):
    """
    Extract user identification from request.

    Tries Matomo tracker ID first (if user opted in), falls back to IP address.

    Args:
        request: Gradio Request object

    Returns:
        tuple: (user_id, session_id) - either can be None
    """
    if request:
        # Try to get Matomo visitor ID for privacy-respecting tracking
        if hasattr(request, "cookies"):
            user_id = get_matomo_tracker_from_cookies(request.cookies)
        else:
            # Fallback to IP address
            try:
                user_id = get_ip(request)
            except:
                user_id = None
        # Get Gradio session hash (unique per session, not per user)
        session_id = getattr(request, "session_hash", None)
    else:
        session_id = None
        user_id = None
    return user_id, session_id


class AppState:
    """
    Application state for an ongoing session.

    Tracks the current comparison mode, model selections, user preferences, and reactions.
    """

    def __init__(
        self,
        awaiting_responses=False,
        model_left=None,
        model_right=None,
        category=None,
        custom_models_selection=None,
        mode="random",
    ):
        """
        Initialize application state.

        Args:
            awaiting_responses: Whether waiting for model responses
            model_left: Model name for left position
            model_right: Model name for right position
            category: User's selected prompt category
            custom_models_selection: User's custom model selection if in custom mode
            mode: Selection mode (random, big-vs-small, small-models, reasoning, custom)
        """
        self.awaiting_responses = awaiting_responses
        self.model_left = model_left
        self.model_right = model_right
        self.category = category
        self.mode = mode
        self.custom_models_selection = custom_models_selection
        # Store reactions (likes/dislikes) on individual messages
        self.reactions = []

    # def to_dict(self) -> dict:
    #     return self.__dict__.copy()


def pick_models(mode, custom_models_selection, unavailable_models):
    """
    Select two models based on the comparison mode.

    Supports multiple selection modes:
    - random: Two random models
    - big-vs-small: One large model vs one small model
    - small-models: Two small models
    - reasoning: Two reasoning-capable models
    - custom: User-specified models

    Args:
        mode: Selection mode string
        custom_models_selection: User's custom model choices (if custom mode)
        unavailable_models: Models that are currently unavailable/offline

    Returns:
        list: [model_left, model_right] - pair of model names, randomly swapped
    """
    import random

    from backend.models.data import get_models

    models = get_models()
    big_models = models.big_models
    random_pool = models.random_models
    small_models = models.small_models

    if mode == "big-vs-small":
        # Compare large models against small models
        model_left_name = choose_among(models=big_models, excluded=unavailable_models)
        model_right_name = choose_among(
            models=small_models, excluded=unavailable_models
        )

    elif mode == "small-models":
        # Compare two small models
        model_left_name = choose_among(models=small_models, excluded=unavailable_models)
        model_right_name = choose_among(
            models=small_models, excluded=unavailable_models + [model_left_name]
        )

    elif mode == "custom" and len(custom_models_selection) > 0:
        # User-selected models
        # FIXME: input sanitization needed
        # if any(mode[1], not in models):
        #     raise Exception(f"Model choice from value {str(model_dropdown_scoped)} not among possibilities")

        if len(custom_models_selection) == 1:
            # One model chosen by user, pair with random model
            model_left_name = custom_models_selection[0]
            model_right_name = choose_among(
                models=random_pool,
                excluded=[custom_models_selection[0]] + unavailable_models,
            )
        elif len(custom_models_selection) == 2:
            # Two models chosen by user
            model_left_name = custom_models_selection[0]
            model_right_name = custom_models_selection[1]

    else:
        # Default to random mode
        model_left_name = choose_among(models=random_pool, excluded=unavailable_models)
        model_right_name = choose_among(
            models=random_pool, excluded=[model_left_name] + unavailable_models
        )

    # Randomly swap models to avoid position bias
    swap = random.randint(0, 1)
    if swap == 1:
        model_right_name, model_left_name = model_left_name, model_right_name

    return [model_left_name, model_right_name]


def get_api_key(endpoint: "Endpoint"):
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

    # "api_type": "huggingface/cohere" doesn't work, using the openai api type and api_base="https://router.huggingface.co/cohere/compatibility/v1/"
    if endpoint.get("api_base") and "albert.api.etalab.gouv.fr" in endpoint.get(
        "api_base"
    ):
        return os.getenv("ALBERT_KEY")
    # HuggingFace Inference API
    if endpoint.get("api_base") and "huggingface.co" in endpoint.get("api_base"):
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
        messages: List of ChatMessage objects

    Returns:
        int: Total output tokens generated by the model
    """
    # Add up output_tokens from metadata of all assistant messages
    total_output_tokens = sum(
        msg.metadata.get("output_tokens", 0) or 0
        for msg in messages
        if msg.role == "assistant"
    )
    return total_output_tokens


def to_threeway_chatbot(conversations):
    """
    Convert two conversations into a single alternating chatbot view.

    Merges two parallel conversations (model A and B) into a single chat history
    showing user messages alternating with bot responses from both models.
    Format: [User Q1, Bot A Response, Bot B Response, User Q2, Bot A Response, Bot B Response, ...]

    Args:
        conversations: Tuple of two Conversation objects with messages

    Returns:
        list: Merged chatbot messages with model identifier in metadata
    """
    threeway_chatbot = []
    # Extract non-system messages from both conversations
    conv_a_messages = [
        message for message in conversations[0].messages if message.role != "system"
    ]
    conv_b_messages = [
        message for message in conversations[1].messages if message.role != "system"
    ]

    # Zip conversations together - assumes same number of turns in both
    for msg_a, msg_b in zip(conv_a_messages, conv_b_messages):
        if msg_a.role == "user":
            # Both should have user message at same turn
            # Could even test if msg_a == msg_b (they should be identical)
            if msg_b.role != "user":
                raise IndexError
            # Add user message (same for both models)
            threeway_chatbot.append(msg_a)
        else:
            # Both are bot responses
            if msg_a:
                # Tag with model A identifier
                msg_a.metadata.update({"bot": "a"})
                threeway_chatbot.append(
                    {
                        "role": "assistant",
                        "content": msg_a.content,
                        "error": msg_a.error,
                        "reasoning": msg_a.reasoning,
                        "metadata": msg_a.metadata,
                    }
                )
            if msg_b:
                # Tag with model B identifier
                msg_b.metadata.update({"bot": "b"})
                threeway_chatbot.append(
                    {
                        "role": "assistant",
                        "content": msg_b.content,
                        "error": msg_a.error,  # Note: Uses msg_a.error, might be bug?
                        "reasoning": msg_b.reasoning,
                        "metadata": msg_b.metadata,
                    }
                )
    return threeway_chatbot
