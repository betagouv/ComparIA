import os
from pathlib import Path
from typing import Literal, get_args

from httpx import Timeout
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    LANGUIA_DEBUG: bool = False
    LANGUIA_CONTROLLER_URL: str | None = "http://localhost:21001"
    COMPARIA_REDIS_HOST: str = "localhost"
    MOCK_RESPONSE: bool = False
    LOGDIR: Path = ROOT_DIR / "data"
    LOG_FORMAT: Literal["JSON", "RAW"] = "JSON"
    COMPARIA_DB_URI: str | None = None
    GIT_COMMIT: str | None = None
    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str = "dev"
    SENTRY_SAMPLE_RATE: float = 0.2
    OPENROUTER_API_KEY: str | None = None
    ALBERT_KEY: str | None = None
    HF_INFERENCE_KEY: str | None = None
    ORDBOGEN_API_KEY: str | None = None
    HF_PUSH_DATASET_KEY: str = ""
    HF_PUSH_DATASET_PATH: str = ""

    DEFAULT_COUNTRY_PORTAL: str = "fr"

    RANKING_INTERVAL_SECONDS: int = 3600  # 1 hour
    REPO_ORG: str = "ministere-culture"
    ALTCHA_HMAC_KEY: str = ""

# Response caching
    CACHE_ENABLED: bool = False
    CACHE_PROBABILITY: float = 0.5  # Probability of serving a cached response on hit
    CACHE_TTL: int = 172800  # Cache TTL in seconds (default 48h)
    CACHE_MAX_RESPONSES: int = 5  # Max cached responses per (model, prompt) pair


settings = Settings()

# Generate a random HMAC key if not configured (dev mode)
if not settings.ALTCHA_HMAC_KEY:
    import secrets

    settings.ALTCHA_HMAC_KEY = secrets.token_hex(32)

# Create directory for JSON backup files
os.makedirs(settings.LOGDIR, exist_ok=True)

# HTTP timeout for API calls to LLM providers
# Structure: total timeout, read, write, connect (all in seconds)
GLOBAL_TIMEOUT = Timeout(15.0, read=15.0, write=5.0, connect=15.0)
STREAM_TIMEOUT = 30
ORDBOGEN_GLOBAL_TIMEOUT = Timeout(60.0, read=60.0, write=5.0, connect=15.0)
ORDBOGEN_STREAM_TIMEOUT = 60

# Preferences
PositivePref = Literal["useful", "complete", "creative", "clear_formatting"]
POSITIVE_PREFS: tuple[PositivePref, ...] = get_args(PositivePref)
NegativePref = Literal["incorrect", "superficial", "instructions_not_followed"]
NEGATIVE_PREFS: tuple[NegativePref, ...] = get_args(NegativePref)
ALL_PREFS = POSITIVE_PREFS + NEGATIVE_PREFS

# Available country portals
CountryPortal = Literal["fr", "da"]
COUNTRY_PORTALS: tuple[CountryPortal, ...] = get_args(CountryPortal)
DEFAULT_COUNTRY_PORTAL: CountryPortal = settings.DEFAULT_COUNTRY_PORTAL  # type: ignore[assignment]

# Per-portal objectives for data collection (rows to collect)
OBJECTIVES: dict[CountryPortal, int] = {"fr": 300_000, "da": 10_000}


# Language model selection modes
SelectionMode = Literal["random", "big-vs-small", "small-models", "custom"]
SELECTION_MODES: tuple[SelectionMode, ...] = get_args(SelectionMode)
DEFAULT_SELECTION_MODE: SelectionMode = "random"

# Language model custom selection (tuple of 0, 1, or 2 model IDs, or None)
CustomModelsSelection = tuple[str, ...] | None

# Model parameter thresholds for categorization
SMALL_MODELS_BUCKET_UPPER_LIMIT = 60  # Models with <= 60B params
BIG_MODELS_BUCKET_LOWER_LIMIT = 100  # Models with >= 100B params

# Rate limiting specifically for expensive models (openai models, etc.)
RATELIMIT_PRICEY_MODELS_INPUT = 50_000

# Rate limiting for custom model selection per IP
RATELIMIT_CUSTOM_SELECTION_PER_HOUR = 3
RATELIMIT_CUSTOM_SELECTION_PER_DAY = 5

# Character limit for blind mode (comparison without model names)
BLIND_MODE_INPUT_CHAR_LEN_LIMIT = 60_000

# Altcha PoW CAPTCHA settings
ALTCHA_MAX_NUMBER = 100_000  # Difficulty: ~0.5s on good devices, ~2-3s on low-end
ALTCHA_CHALLENGE_EXPIRY_SECONDS = 600  # 10 minutes
ALTCHA_REPLAY_TTL_SECONDS = 3600  # 1 hour Redis TTL for used challenges
