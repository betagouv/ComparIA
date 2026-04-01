import os
from pathlib import Path
from typing import Literal, TypedDict, get_args

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
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    VERTEXAI_LOCATION: str | None = None
    ALBERT_KEY: str | None = None
    HF_INFERENCE_KEY: str | None = None
    ORDBOGEN_API_KEY: str | None = None
    HF_PUSH_DATASET_KEY: str = ""
    HF_PUSH_DATASET_KEY_DA: str = ""

    RANKING_INTERVAL_SECONDS: int = 3600  # 1 hour

    enable_postgres_handler: bool = True

    # Response caching
    CACHE_ENABLED: bool = False
    CACHE_PROBABILITY: float = 0.5  # Probability of serving a cached response on hit
    CACHE_TTL: int = 172800  # Cache TTL in seconds (default 48h)
    CACHE_MAX_RESPONSES: int = 5  # Max cached responses per (model, prompt) pair


settings = Settings()

# Create directory for JSON backup files
os.makedirs(settings.LOGDIR, exist_ok=True)

# HTTP timeout for API calls to LLM providers
# Structure: total timeout, read, write, connect (all in seconds)
GLOBAL_TIMEOUT = Timeout(15.0, read=15.0, write=5.0, connect=15.0)

# Preferences
PositivePref = Literal["useful", "complete", "creative", "clear_formatting"]
POSITIVE_PREFS: tuple[PositivePref, ...] = get_args(PositivePref)
NegativePref = Literal["incorrect", "superficial", "instructions_not_followed"]
NEGATIVE_PREFS: tuple[NegativePref, ...] = get_args(NegativePref)
ALL_PREFS = POSITIVE_PREFS + NEGATIVE_PREFS

# Available country portals
CountryPortal = Literal["fr", "da"]
COUNTRY_PORTALS: tuple[CountryPortal, ...] = get_args(CountryPortal)
DEFAULT_COUNTRY_PORTAL: CountryPortal = "fr"

# Per-portal objectives for data collection (rows to collect)
OBJECTIVES: dict[CountryPortal, int] = {"fr": 300_000, "da": 10_000}


# Per-portal dataset infos
class PortalRepo(TypedDict):
    org: str | None
    name: str
    token: str


PORTAL_DATASET_INFOS: dict[CountryPortal, PortalRepo] = {
    "fr": {
        "org": "ministere-culture",
        "name": "comparia",
        "token": settings.HF_PUSH_DATASET_KEY,
    },
    "da": {
        "org": "danish-foundation-models",
        "name": "ai-arenaen",
        "token": settings.HF_PUSH_DATASET_KEY_DA,
    },
}

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

# Character limit for blind mode (comparison without model names)
BLIND_MODE_INPUT_CHAR_LEN_LIMIT = 60_000
