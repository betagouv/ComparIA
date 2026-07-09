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
    SENTRY_SAMPLE_RATE: float = 0.1
    LINKUP_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    ALBERT_KEY: str | None = None
    HF_INFERENCE_KEY: str | None = None
    ORDBOGEN_API_KEY: str | None = None
    HF_PUSH_DATASET_KEY: str = ""
    HF_PUSH_DATASET_PATH: str = ""

    DEFAULT_COUNTRY_PORTAL: str = "fr"

    RANKING_INTERVAL_SECONDS: int = 3600  # 1 hour
    REPO_ORG: str = "ministere-culture"
    VOTES_OBJECTIVE: int = 300_000
    ALTCHA_HMAC_KEY: str = ""

    # Content-safety guardrail (Nemotron via OpenRouter). No-ops without OPENROUTER_API_KEY.
    # ENABLED runs the check and records the verdict (shadow mode); ENFORCE must
    # also be on for an egregious prompt to actually be blocked. Ship in shadow
    # first, watch the verdicts, then turn ENFORCE on.
    GUARDRAIL_ENABLED: bool = True
    GUARDRAIL_ENFORCE: bool = False
    GUARDRAIL_MODEL: str = "openrouter/nvidia/nemotron-3.5-content-safety:free"
    GUARDRAIL_TIMEOUT: float = 2.5

    # Auth
    # "anonymous_first": sign-in optional; "sign_in_required": blocks /arena/* without session
    ADMIN_EMAILS: list[str] = []
    AUTH_ACCESS_POLICY: Literal["anonymous_first", "sign_in_required"] = (
        "anonymous_first"
    )
    # If non-empty, only emails from these domains can request a login code (e.g. ["beta.gouv.fr"])
    AUTH_DOMAIN_ALLOWLIST: list[str] = []
    AUTH_SESSION_LENGTH_DAYS: int = 30
    # Bumping this value invalidates existing consent logs and forces re-consent
    AUTH_TERMS_VERSION: str = "1.0"
    # Public app origin, used to build absolute links in emails (e.g. invite links)
    COMPARIA_APP_URL: str = "http://localhost:5173"

    @field_validator("COMPARIA_APP_URL")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    # Anonymous
    ANONYMOUS_SESSION_LENGTH_DAYS: int = 30

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

# Preferences
PositivePref = Literal["useful", "complete", "creative", "clear_formatting"]
POSITIVE_PREFS: tuple[PositivePref, ...] = get_args(PositivePref)
NegativePref = Literal["incorrect", "superficial", "instructions_not_followed"]
NEGATIVE_PREFS: tuple[NegativePref, ...] = get_args(NegativePref)
AllPref = Literal[PositivePref | NegativePref]
ALL_PREFS: tuple[AllPref, ...] = POSITIVE_PREFS + NEGATIVE_PREFS
TurnChoice = Literal["both_good", "both_bad", "a_better", "b_better", "idk"]
TURN_CHOICE: tuple[TurnChoice, ...] = get_args(TurnChoice)

# FIXME equivalences legacy?
# # Reference data for scaled equivalences
# # Population using generative AI
# # FIXME make generic (env var or db field)
# CONSUMPTION_SCALE_FACTOR: Final[float] = {
#     # 48% of ppl aged 12 or more in 2026 https://www.credoc.fr/publications/barometre-du-numerique-2026-rapport
#     # population count of 12 or more in 2024 https://www.insee.fr/fr/statistiques/7746192?sommaire=7746197
#     "fr": 59_315_947 * 0.48,
#     # 48.4% of ppl aged 16–74 in 2025 https://ec.europa.eu/eurostat/fr/web/products-eurostat-news/w/ddn-20251216-3
#     # population count of 16-74 https://en.wikipedia.org/wiki/Demographics_of_Denmark
#     "da": 4_350_000 * 0.484,
# }[settings.DEFAULT_COUNTRY_PORTAL]

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

# Cooldown for IPs that hit the content-safety guardrail too often (abuse /
# jailbreak probing). Counts only enforced blocks in a rolling window; once an
# IP crosses the threshold it is cooled down for the rest of the window WITHOUT
# calling the guardrail (protects OpenRouter quota). Kept generous because gov
# users share NAT IPs (hospitals, ministries) and must not be locked out.
RATELIMIT_BLOCKED_PROMPTS_PER_HOUR = 15

# Character limit for blind mode (comparison without model names)
BLIND_MODE_INPUT_CHAR_LEN_LIMIT = 60_000

# Altcha PoW CAPTCHA settings
ALTCHA_MAX_NUMBER = 100_000  # Difficulty: ~0.5s on good devices, ~2-3s on low-end
ALTCHA_CHALLENGE_EXPIRY_SECONDS = 600  # 10 minutes
ALTCHA_REPLAY_TTL_SECONDS = 3600  # 1 hour Redis TTL for used challenges

# Web search intro for LLM
WEB_SEARCH_INTRO = "Here is some recent information from a web search. Use it to answer the user's question if it's relevant:\n\n"
