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
import sys

import sentry_sdk

from backend import logger

# Models that should not be sampled/selected (can be populated from config)
unavailable_models = []


if os.getenv("GIT_COMMIT"):
    git_commit = os.getenv("GIT_COMMIT")
else:
    git_commit = None

if os.getenv("SENTRY_SAMPLE_RATE"):
    traces_sample_rate = float(os.getenv("SENTRY_SAMPLE_RATE"))
else:
    traces_sample_rate = 0.2

profiles_sample_rate = traces_sample_rate

if os.getenv("SENTRY_DSN"):
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    if os.getenv("SENTRY_ENV"):
        sentry_env = os.getenv("SENTRY_ENV")
    else:
        sentry_env = "development"
    sentry_sdk.init(
        release=git_commit,
        attach_stacktrace=True,
        dsn=os.getenv("SENTRY_DSN"),
        environment=sentry_env,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        project_root=os.getcwd(),
    )
    logger.debug(
        "Sentry loaded with traces_sample_rate="
        + str(traces_sample_rate)
        + " and profiles_sample_rate="
        + str(profiles_sample_rate)
        + " for release "
        + str(git_commit)
    )


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
