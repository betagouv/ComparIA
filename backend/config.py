import os
from pathlib import Path
from typing import Literal, get_args

from httpx import Timeout
from pydantic_settings import BaseSettings

BACKEND_PATH = Path(__file__).parent
ROOT_PATH = BACKEND_PATH.parent
FRONTEND_PATH = ROOT_PATH / "frontend"

MODELS_DATA_PATH = ROOT_PATH / "utils" / "models" / "generated-models.json"


class Settings(BaseSettings):
    LANGUIA_DEBUG: bool = False
    LANGUIA_CONTROLLER_URL: str | None = "http://localhost:21001"
    COMPARIA_REDIS_HOST: str = "localhost"
    MOCK_RESPONSE: bool = False
    LOGDIR: Path = ROOT_PATH / "data"
    LOG_FORMAT: Literal["JSON", "RAW"] = "JSON"
    COMPARIA_DB_URI: str | None = None
    GIT_COMMIT: str | None = None
    SENTRY_DSN: str | None = None
    SENTRY_ENV: str = "development"
    SENTRY_SAMPLE_RATE: float = 0.2
    OPENROUTER_API_KEY: str | None = None
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    VERTEXAI_LOCATION: str | None = None
    ALBERT_KEY: str | None = None
    HF_INFERENCE_KEY: str | None = None
    HF_PUSH_DATASET_KEY: str = ""
    REPO_ORG: str = "ministere-culture"

    enable_postgres_handler: bool = True


settings = Settings()

# Create directory for JSON backup files
os.makedirs(settings.LOGDIR, exist_ok=True)

# HTTP timeout for API calls to LLM providers
# Structure: total timeout, read, write, connect (all in seconds)
GLOBAL_TIMEOUT = Timeout(10.0, read=10.0, write=5.0, connect=10.0)

# Available country portals
CountryPortal = Literal["fr", "da"]
COUNTRY_PORTALS: tuple[CountryPortal, ...] = get_args(CountryPortal)
DEFAULT_COUNTRY_PORTAL: CountryPortal = "fr"

# Per-country objectives for data collection (rows to collect)
OBJECTIVES: dict[CountryPortal, int] = {"fr": 250_000, "da": 10_000}

# Language model selection modes
SelectionMode = Literal["random", "big-vs-small", "small-models", "custom"]
SELECTION_MODES: tuple[SelectionMode, ...] = get_args(SelectionMode)
DEFAULT_SELECTION_MODE: SelectionMode = "random"

# Language model custom selection
CustomModelsSelection = tuple[str] | tuple[str, str] | None

# Model parameter thresholds for categorization
SMALL_MODELS_BUCKET_UPPER_LIMIT = 60  # Models with <= 60B params
BIG_MODELS_BUCKET_LOWER_LIMIT = 100  # Models with >= 100B params

# Rate limiting specifically for expensive models (openai models, etc.)
RATELIMIT_PRICEY_MODELS_INPUT = 50_000

# Character limit for blind mode (comparison without model names)
BLIND_MODE_INPUT_CHAR_LEN_LIMIT = 60_000
