import os
from pathlib import Path
from typing import Literal, get_args

from httpx import Timeout
from pydantic import field_validator
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
    LOGDIR: Path = ROOT_DIR / "logs"
    LOG_FORMAT: Literal["JSON", "RAW"] = "JSON"
    COMPARIA_DB_URI: str | None = None
    GIT_COMMIT: str | None = None
    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str = "dev"
    SENTRY_SAMPLE_RATE: float = 1.0
    LINKUP_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    MISTRAL_API_KEY: str | None = None
    ALBERT_KEY: str | None = None
    HF_INFERENCE_KEY: str | None = None
    ORDBOGEN_API_KEY: str | None = None

    # Names the deployment (fr, da, a museum one-off, ...). Used as the Redis key
    # namespace and to seed the default locale. Renamed from DEFAULT_COUNTRY_PORTAL,
    # which described a country portal the project outgrew; the deployment manifests
    # have to carry the new name, since nothing falls back to the old one. The
    # values themselves are unchanged, so Redis keys stay put.
    COMPARIA_INSTANCE_NAME: str = "fr"

    # Display currency. Model prices are stored in euros and converted for the UI.
    DISPLAY_CURRENCY: str = "EUR"
    DISPLAY_CURRENCY_RATE_FROM_EUR: float | None = None
    EXCHANGE_RATE_API_URL: str = "https://api.frankfurter.dev/v2"
    EXCHANGE_RATE_CACHE_SECONDS: int = 86_400

    RANKING_INTERVAL_SECONDS: int = 3600  # 1 hour
    REPO_ORG: str = "ministere-culture"
    VOTES_OBJECTIVE: int = 300_000
    ALTCHA_HMAC_KEY: str = ""

    # Auth
    # "anonymous_first": sign-in optional; "sign_in_required": blocks /arena/* without session
    ADMIN_EMAILS: list[str] = []
    AUTH_ACCESS_POLICY: Literal["anonymous_first", "sign_in_required"] = (
        "anonymous_first"
    )
    # If non-empty, only emails from these domains can request a login code (e.g. ["beta.gouv.fr"])
    AUTH_DOMAIN_ALLOWLIST: list[str] = []
    AUTH_SESSION_LENGTH_DAYS: int = 30

    # Deliberately high: keyed on IP, so a school class behind one shared NAT
    # must never be locked out. The real anti-abuse limit is per-email below.
    AUTH_EMAIL_REQUEST_PER_IP_PER_HOUR: int = 2000
    AUTH_EMAIL_REQUEST_PER_EMAIL_PER_HOUR: int = 5
    AUTH_VERIFY_MAX_ATTEMPTS: int = 5

    # Anonymous
    ANONYMOUS_SESSION_LENGTH_DAYS: int = 30

    # Public app origin, used to build absolute links in emails (e.g. invite links)
    COMPARIA_APP_URL: str = "http://localhost:5173"

    @field_validator("COMPARIA_APP_URL")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    # SMTP (Brevo relay or any SMTP provider)
    # If unset, login codes are logged to console instead of being sent by email
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_STARTTLS: bool = True
    EMAIL_FROM: str = "noreply@comparia.beta.gouv.fr"
    EMAIL_FROM_NAME: str = "ComparIA"

    # Response caching
    CACHE_ENABLED: bool = False
    CACHE_PROBABILITY: float = 0.5  # Probability of serving a cached response on hit
    CACHE_TTL: int = 172800  # Cache TTL in seconds (default 48h)
    CACHE_MAX_RESPONSES: int = 5  # Max cached responses per (model, prompt) pair

    @field_validator("DISPLAY_CURRENCY")
    @classmethod
    def validate_display_currency(cls, value: str) -> str:
        currency = value.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("DISPLAY_CURRENCY must be a three-letter ISO 4217 code")
        return currency

    @field_validator("DISPLAY_CURRENCY_RATE_FROM_EUR")
    @classmethod
    def validate_manual_currency_rate(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("DISPLAY_CURRENCY_RATE_FROM_EUR must be greater than zero")
        return value

    @field_validator("EXCHANGE_RATE_CACHE_SECONDS")
    @classmethod
    def validate_exchange_rate_cache_seconds(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("EXCHANGE_RATE_CACHE_SECONDS must be greater than zero")
        return value


settings = Settings()

# Generate a random HMAC key if not configured (dev mode)
if not settings.ALTCHA_HMAC_KEY:
    import secrets

    settings.ALTCHA_HMAC_KEY = secrets.token_hex(32)

# Create directory for JSON backup files
os.makedirs(settings.LOGDIR, exist_ok=True)


# Cookies
ANONYMOUS_SESSION_COOKIE = "anonymous_session"

# HTTP timeout for API calls to LLM providers
# Structure: total timeout, read, write, connect (all in seconds)
GLOBAL_TIMEOUT = Timeout(15.0, read=15.0, write=5.0, connect=15.0)
STREAM_TIMEOUT = 30
ORDBOGEN_GLOBAL_TIMEOUT = Timeout(60.0, read=60.0, write=5.0, connect=15.0)
ORDBOGEN_STREAM_TIMEOUT = 60

# Vote
# The tags a voter can attach are in the 'vote_tag' table, not here: an
# operator edits them without a deploy. See utils/database/models/vote_tag.py.
TurnChoice = Literal["both_good", "both_bad", "a_better", "b_better", "idk"]
TURN_CHOICE: tuple[TurnChoice, ...] = get_args(TurnChoice)

# Language model selection modes
SelectionMode = Literal["random", "big-vs-small", "small-models", "custom"]
SELECTION_MODES: tuple[SelectionMode, ...] = get_args(SelectionMode)
DEFAULT_SELECTION_MODE: SelectionMode = "random"

# Language model custom selection (tuple of 0, 1, or 2 model IDs, or None)
CustomModelsSelection = tuple[str, ...] | None

# Model parameter thresholds for categorization
SMALL_MODELS_BUCKET_UPPER_LIMIT = 60  # Models with <= 60B params
BIG_MODELS_BUCKET_LOWER_LIMIT = 100  # Models with >= 100B params

# Rate limiting specifically for expensive models (openai models, etc.).
# Keyed per anonymous session (the `anonymous_session` cookie hash), not per IP,
# so users behind a shared NAT (schools, hospitals) each get their own budget.
RATELIMIT_PRICEY_MODELS_INPUT = 50_000

# Cooldown for IPs that trip a prompt check too often (abuse / jailbreak
# probing). Counts only blocks in a rolling window; once an IP crosses the
# threshold it is cooled down for the rest of the window WITHOUT calling the
# moderation API (protects the quota). Kept generous because gov users share NAT
# IPs (hospitals, ministries) and must not be locked out.
RATELIMIT_BLOCKED_PROMPTS_PER_HOUR = 15

# Character limit for blind mode (comparison without model names)
BLIND_MODE_INPUT_CHAR_LEN_LIMIT = 60_000

# Altcha PoW CAPTCHA settings
ALTCHA_MAX_NUMBER = 100_000  # Difficulty: ~0.5s on good devices, ~2-3s on low-end
ALTCHA_CHALLENGE_EXPIRY_SECONDS = 600  # 10 minutes
ALTCHA_REPLAY_TTL_SECONDS = 3600  # 1 hour Redis TTL for used challenges

# Web search intro for LLM
WEB_SEARCH_INTRO = "Here is some recent information from a web search. Use it to answer the user's question if it's relevant:\n\n"
