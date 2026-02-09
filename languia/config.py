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
import sentry_sdk
import json5
import sys
import datetime
from pathlib import Path
import logging
from logging.handlers import WatchedFileHandler
from languia.logs import JSONFormatter, PostgresHandler
from httpx import Timeout
from languia.models import filter_enabled_models

# HTTP timeout for API calls to LLM providers
# Structure: total timeout, read, write, connect (all in seconds)
GLOBAL_TIMEOUT = Timeout(10.0, read=10.0, write=5.0, connect=10.0)

# Per-country objectives for data collection (rows to collect)
OBJECTIVES = {"fr": 300_000, "da": 10_000}

# Model parameter thresholds for categorization
SMALL_MODELS_BUCKET_UPPER_LIMIT = 60  # Models with <= 60B params
BIG_MODELS_BUCKET_LOWER_LIMIT = 100  # Models with >= 100B params

# Debug mode flag from environment variable
env_debug = os.getenv("LANGUIA_DEBUG")

# Rate limiting specifically for expensive models (openai models, etc.)
RATELIMIT_PRICEY_MODELS_INPUT = 50_000

# Character limit for blind mode (comparison without model names)
BLIND_MODE_INPUT_CHAR_LEN_LIMIT = 60_000

# Models that should not be sampled/selected (can be populated from config)
unavailable_models = []

# Parse debug flag from environment
if env_debug:
    debug = env_debug.lower() == "true"
else:
    debug = False

# Log file naming with hostname and timestamp
t = datetime.datetime.now()
hostname = os.uname().nodename
log_filename = f"logs-{hostname}-{t.year}-{t.month:02d}-{t.day:02d}.jsonl"

# Directory for local JSON log files (fallback storage)
LOGDIR = os.getenv("LOGDIR", "./data")

# PostgreSQL connection string for database persistence
db = os.getenv("COMPARIA_DB_URI", None)

# Enable PostgreSQL logging handler (can be disabled for testing)
enable_postgres_handler = True


def build_logger(logger_filename):
    """
    Configure and initialize application logger with multiple handlers.

    Sets up three logging destinations:
    1. Console (stdout) - human-readable format
    2. File (JSONL) - structured JSON for log analysis
    3. PostgreSQL - centralized database logging

    The logger uses different formatting for console vs file:
    - Console: Human-readable timestamp and function name
    - File: Structured JSON with request context

    Args:
        logger_filename: Filename for JSONL log output (relative to LOGDIR)

    Returns:
        Logger: Configured logger instance for "languia"

    Environment Variables:
        - LANGUIA_DEBUG: Set to "true" for DEBUG level, "false" for INFO
        - LOGDIR: Directory for log files (default "./data")
        - COMPARIA_DB_URI: PostgreSQL connection string for database logging
    """
    # TODO: log "funcName"
    logger = logging.getLogger("languia")
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    # Use a more human-readable format for the console.
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Récupérer le format de logs depuis la variable d'environnement
    log_format = os.getenv("LOG_FORMAT", "JSON").upper()

    if LOGDIR:
        os.makedirs(LOGDIR, exist_ok=True)
        filename = os.path.join(LOGDIR, logger_filename)
        file_handler = WatchedFileHandler(filename, encoding="utf-8")

        # Choisir le formatter en fonction de LOG_FORMAT
        if log_format == "RAW":
            # Format identique à la console pour une meilleure lisibilité en dev
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            # Format JSON par défaut pour l'analyse automatisée
            file_formatter = JSONFormatter(
                '{"time":"%(asctime)s", "name": "%(name)s", \
                "level": "%(levelname)s", "message": "%(message)s"}',
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    if db and enable_postgres_handler:
        postgres_handler = PostgresHandler(db)
        logger.addHandler(postgres_handler)

    return logger


def configure_uvicorn_logging():
    """
    Configure uvicorn/FastAPI loggers to use the same handlers as languia logger.

    Redirects uvicorn.access and uvicorn.error logs to the same backends:
    - File (JSON or RAW format based on LOG_FORMAT env var)
    - PostgreSQL (if configured)
    - Console (stdout)

    Call this after build_logger() to ensure uvicorn logs are captured.
    """
    log_format = os.getenv("LOG_FORMAT", "JSON").upper()

    # Configure uvicorn loggers
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = False

        if debug:
            uvicorn_logger.setLevel(logging.DEBUG)
        else:
            uvicorn_logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        uvicorn_logger.addHandler(console_handler)

        # File handler
        if LOGDIR:
            os.makedirs(LOGDIR, exist_ok=True)
            t = datetime.datetime.now()
            hostname = os.uname().nodename
            uvicorn_log_filename = f"uvicorn-{hostname}-{t.year}-{t.month:02d}-{t.day:02d}.jsonl"
            filename = os.path.join(LOGDIR, uvicorn_log_filename)
            file_handler = WatchedFileHandler(filename, encoding="utf-8")

            if log_format == "RAW":
                file_formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            else:
                file_formatter = JSONFormatter(
                    '{"time":"%(asctime)s", "name": "%(name)s", \
                    "level": "%(levelname)s", "message": "%(message)s"}',
                    datefmt="%Y-%m-%d %H:%M:%S",
                )

            file_handler.setFormatter(file_formatter)
            uvicorn_logger.addHandler(file_handler)

        # PostgreSQL handler
        if db and enable_postgres_handler:
            postgres_handler = PostgresHandler(db)
            uvicorn_logger.addHandler(postgres_handler)


logger = build_logger(log_filename)
configure_uvicorn_logging()

# Configurer le logger frontend pour utiliser les mêmes handlers
frontend_logger = logging.getLogger("frontend")
frontend_logger.setLevel(logging.DEBUG if debug else logging.INFO)
for handler in logger.handlers:
    frontend_logger.addHandler(handler)

# Log séparateur au démarrage pour marquer les redémarrages
logger.info("=" * 80)

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
