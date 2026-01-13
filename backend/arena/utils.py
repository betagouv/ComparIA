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
