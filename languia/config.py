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

import datetime
import logging
import os
import sys
from logging.handlers import WatchedFileHandler
from pathlib import Path

import json5
import sentry_sdk

from languia.logs import JSONFormatter, PostgresHandler
from languia.models import filter_enabled_models

# Debug mode flag from environment variable
env_debug = os.getenv("LANGUIA_DEBUG")


# Models that should not be sampled/selected (can be populated from config)
unavailable_models = []

# Parse debug flag from environment
if env_debug:
    debug = env_debug.lower() == "true"
else:
    debug = False


# Directory for local JSON log files (fallback storage)
LOGDIR = os.getenv("LOGDIR", "./data")

# PostgreSQL connection string for database persistence
db = os.getenv("COMPARIA_DB_URI", None)

# Enable PostgreSQL logging handler (can be disabled for testing)
enable_postgres_handler = True

if os.getenv("GIT_COMMIT"):
    git_commit = os.getenv("GIT_COMMIT")
else:
    git_commit = None

if not debug:
    assets_absolute_path = "/app/assets"
else:
    assets_absolute_path = os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    )
    # print("assets_absolute_path: "+assets_absolute_path)
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

# Load model definitions from generated configuration
# File contains metadata: params, pricing, reasoning capability, licenses, etc.
all_models_data = json5.loads(Path("./utils/models/generated-models.json").read_text())

# Filter to only enabled models (removes disabled or deprecated models)
models = filter_enabled_models(all_models_data["models"])


# All models (for standard random selection)
random_pool = [id for id, _model in models.items()]

# Models with parameters <= 60B (for "small-models" selection mode)
small_models = [
    id
    for id, model in models.items()
    if model["params"] <= SMALL_MODELS_BUCKET_UPPER_LIMIT
]

# Models with parameters >= 100B (for "big-vs-small" selection mode)
big_models = [
    id
    for id, model in models.items()
    if model["params"] >= BIG_MODELS_BUCKET_LOWER_LIMIT
]

# Commercial models with higher API costs (e.g., Claude, GPT-4)
# These have stricter rate limits applied
pricey_models = [id for id, model in models.items() if model.get("pricey", False)]

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
