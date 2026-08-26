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
    COMPARIA_REDIS_HOST: str = "localhost"
    COMPARIA_REDIS_PASSWORD: str | None = None
    MOCK_RESPONSE: bool = False
    LOGDIR: Path = ROOT_DIR / "logs"
    LOG_FORMAT: Literal["JSON", "RAW"] = "JSON"
    COMPARIA_DB_URI: str | None = None
    GIT_COMMIT: str | None = None
    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str = "dev"
    SENTRY_SAMPLE_RATE: float = 0.1
    LINKUP_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    MISTRAL_API_KEY: str | None = None
    HF_INFERENCE_KEY: str | None = None
    ORDBOGEN_API_KEY: str | None = None

    # Names the deployment (fr, da, a museum one-off, ...). Used as the Redis key
    # namespace and to seed the default locale. Renamed from DEFAULT_COUNTRY_PORTAL,
    # which described a country portal the project outgrew; the deployment manifests
    # have to carry the new name, since nothing falls back to the old one. The
    # values themselves are unchanged, so Redis keys stay put.
    COMPARIA_INSTANCE_NAME: str = "fr"

    # Display currency. Model prices are stored in US dollars and converted for the UI.
    DISPLAY_CURRENCY: str = "EUR"
    DISPLAY_CURRENCY_RATE_FROM_USD: float | None = None
    EXCHANGE_RATE_API_URL: str = "https://api.frankfurter.dev/v2"
    EXCHANGE_RATE_CACHE_SECONDS: int = 86_400

    RANKING_INTERVAL_SECONDS: int = 3600  # 1 hour
    VOTES_OBJECTIVE: int = 300_000
    ALTCHA_HMAC_KEY: str = ""

    # Dataset publishing. The schedule itself lives in the admin panel; these
    # are the boundaries the run gets on the machine. Off here, a larger
    # deployment can run this same image as a dedicated scheduler replica.
    DATASET_SCHEDULER_ENABLED: bool = True
    DATASET_RUN_TIMEOUT: int = 6 * 3600
    DATASET_MEMORY_LIMIT_GB: int = 8
    # Generous: the export's single read walks the whole comparison table, and
    # this is here to end a query that has stopped moving, not a slow one.
    DATASET_STATEMENT_TIMEOUT_MS: int = 2 * 3600 * 1000

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
    # Ceiling on wrong codes per email, whatever the source IP. The per-IP counter
    # above only slows one attacker down; this one closes the login code itself.
    AUTH_VERIFY_MAX_ATTEMPTS_PER_EMAIL: int = 10

    # Anonymous
    ANONYMOUS_SESSION_LENGTH_DAYS: int = 30

    # Public app origin, used to build absolute links in emails (e.g. invite links)
    COMPARIA_APP_URL: str = "http://localhost:5173"

    # Number of reverse proxies in front of the app. X-Forwarded-For is only read
    # when this is > 0, and only the entry the outermost trusted proxy appended is
    # kept, so a client cannot pick its own IP by sending the header itself.
    # Set it to the real number of hops in every deployment (1 behind Caddy alone).
    COMPARIA_TRUSTED_PROXY_COUNT: int = 0

    # Session cookies carry the Secure flag unless this is turned off for local
    # HTTP development. Never tie it to the debug flag: debug logging and cookie
    # security are separate decisions.
    COMPARIA_COOKIE_SECURE: bool = True

    # Extra browser origins allowed to call the API with credentials. The
    # deployments serve the front and the API from one origin through Caddy, so
    # this stays empty outside development.
    COMPARIA_CORS_ORIGINS: list[str] = []

    # When set, /metrics requires "Authorization: Bearer <token>".
    METRICS_TOKEN: str | None = None

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

    @field_validator("DISPLAY_CURRENCY_RATE_FROM_USD")
    @classmethod
    def validate_manual_currency_rate(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("DISPLAY_CURRENCY_RATE_FROM_USD must be greater than zero")
        return value

    @field_validator("EXCHANGE_RATE_CACHE_SECONDS")
    @classmethod
    def validate_exchange_rate_cache_seconds(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("EXCHANGE_RATE_CACHE_SECONDS must be greater than zero")
        return value


settings = Settings()

# A per-process key breaks the captcha across replicas and across restarts, so it
# is a dev-only convenience. Outside debug the deployment has to provide one.
if not settings.ALTCHA_HMAC_KEY:
    if not settings.LANGUIA_DEBUG:
        raise RuntimeError(
            "ALTCHA_HMAC_KEY is required. Generate one with: openssl rand -hex 32"
        )
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

# The per-session budget above is the one that matters, since users behind one
# shared NAT each get their own. But a client that drops the `anonymous_session`
# cookie gets a fresh session on every request, so the same budget also runs per
# IP as a backstop. Twenty times the room, because that IP may be a whole
# building.
RATELIMIT_PRICEY_MODELS_INPUT_PER_IP = RATELIMIT_PRICEY_MODELS_INPUT * 20

# Cheap models are not free either, and only pricey ones used to be counted, so
# nothing at all stopped someone hammering the rest. Wider still: an ordinary
# session must never meet this.
RATELIMIT_ALL_MODELS_INPUT = RATELIMIT_PRICEY_MODELS_INPUT * 10
RATELIMIT_ALL_MODELS_INPUT_PER_IP = RATELIMIT_ALL_MODELS_INPUT * 20

# Cooldown for IPs that trip a prompt check too often (abuse / jailbreak
# probing). Counts only blocks in a rolling window; once an IP crosses the
# threshold it is cooled down for the rest of the window WITHOUT calling the
# moderation API (protects the quota). Kept generous because gov users share NAT
# IPs (hospitals, ministries) and must not be locked out.
RATELIMIT_BLOCKED_PROMPTS_PER_HOUR = 15

# Character limit for blind mode (comparison without model names)
BLIND_MODE_INPUT_CHAR_LEN_LIMIT = 60_000

# Every turn resends the whole transcript to both models, so an endless
# conversation costs more on each message. Cap it.
MAX_TURNS_PER_COMPARISON = 20

# Bounds on the free-text and tag annotations a voter can attach to a turn.
MAX_VOTE_KEYWORD_ANNOTATIONS = 20
MAX_VOTE_CUSTOM_ANNOTATION_LEN = 1_000

# Altcha PoW CAPTCHA settings
ALTCHA_MAX_NUMBER = 100_000  # Difficulty: ~0.5s on good devices, ~2-3s on low-end
ALTCHA_CHALLENGE_EXPIRY_SECONDS = 600  # 10 minutes
ALTCHA_REPLAY_TTL_SECONDS = 3600  # 1 hour Redis TTL for used challenges

# Web search intro for LLM
WEB_SEARCH_INTRO = "Here is some recent information from a web search. Use it to answer the user's question if it's relevant:\n\n"
