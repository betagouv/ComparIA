"""
Configuration and initialization for ComparIA application.

Handles:
- Environment variable parsing
- Logger setup (console, file, PostgreSQL)
- Sentry error tracking configuration
- Model loading and categorization
- Database connection setup
- API timeout settings
- Rate limiting thresholds
"""

import os

from backend import logger

# Models that should not be sampled/selected (can be populated from config)
unavailable_models = []


# HTTP headers for API requests (identifies as FastChat client)
headers = {"User-Agent": "FastChat Client"}

# URL of FastChat controller for local model serving (optional)
# Used when serving models through FastChat instead of external APIs
if os.getenv("LANGUIA_CONTROLLER_URL") is not None:
    controller_url = os.getenv("LANGUIA_CONTROLLER_URL")
else:
    controller_url = "http://localhost:21001"


def get_model_system_prompt(model_name):
    """
    Get model-specific system prompt if configured.

    Allows customization of model behavior through system prompts.
    Currently only specific French models (chocolatine, lfm-40b) have custom prompts.
    Other models use None (no system prompt by default).

    Args:
        model_name: Model identifier (e.g., "openai/gpt-4", "chocolatine")

    Returns:
        str: French system prompt, or None for no custom system prompt

    Note:
        The system prompt is included in conversations when provided.
        This ensures consistent behavior across multiple conversations.
    """
    if "chocolatine" in model_name or "lfm-40b" in model_name:
        # French system prompt for helpful and concise responses
        return "Tu es un assistant IA serviable et bienveillant. Tu fais des réponses concises et précises."
    else:
        return None
