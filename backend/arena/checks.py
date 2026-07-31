"""
The check run on a user prompt before it reaches the arena models.

One call to the Mistral moderation API scores eleven categories between 0 and 1.
Each category carries its own threshold and its own action, configured in the
`prompt_check` table by an admin: `off` (never triggers), `log` (verdict stored
only), `warn` (the user is asked to confirm) and `block` (the prompt is
refused). A prompt takes the strongest action any triggered category asks for.

Fails open: if Mistral errors or times out, the prompt proceeds. Fail-open is
NOT fail-silent: failures are logged at error level, sent to Sentry, and counted
in Redis so the admin panel can show a check that has quietly stopped working.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

import httpx
import sentry_sdk

from backend.config import settings
from utils.database.models.prompt_check import PromptCheck
from utils.database.prompt_checks import get_prompt_check
from utils.storage.redis import (
    REDIS_CHECK_FAILURES_KEY,
    REDIS_CHECK_SCORES_KEY,
    REDIS_CHECK_WARNINGS_KEY,
    get_redis_client,
    hash_content,
)

if TYPE_CHECKING:
    from fastapi import Request

logger = logging.getLogger("languia")

MISTRAL_MODERATION_URL: Final[str] = "https://api.mistral.ai/v1/moderations"
MODERATION_TIMEOUT: Final[float] = 2.5
# How long cached scores stay reusable, i.e. how long the user has to read the
# warning and decide.
SCORES_TTL: Final[int] = 900

# French refusals (platform default locale).
GENERIC_MESSAGE = (
    "Votre message n'a pas pu être envoyé car il enfreint nos conditions "
    "d'utilisation. Veuillez le reformuler."
)
SELF_HARM_MESSAGE = (
    "Si vous traversez une période difficile ou avez des pensées suicidaires, "
    "vous n'êtes pas seul·e. Le 3114, numéro national de prévention du suicide, "
    "est joignable gratuitement et de façon confidentielle 24h/24 et 7j/7."
)
PII_MESSAGE = (
    "Votre message semble contenir des données personnelles. Les messages "
    "envoyés peuvent être publiés dans le jeu de données ouvert."
)

_DECISIONS = {"off": "pass", "log": "logged", "warn": "warned", "block": "blocked"}


async def moderate(text: str, model: str) -> dict[str, float]:
    """Score one prompt with the Mistral moderation API."""
    async with httpx.AsyncClient(timeout=MODERATION_TIMEOUT) as client:
        response = await client.post(
            MISTRAL_MODERATION_URL,
            headers={"Authorization": f"Bearer {settings.MISTRAL_API_KEY}"},
            json={"model": model, "input": [text]},
        )
        response.raise_for_status()
        payload = response.json()

    scores = payload["results"][0]["category_scores"]
    return {category: float(score) for category, score in scores.items()}


@dataclass
class CheckResult:
    """Verdict on one prompt. Persisted on the Turn and logged."""

    decision: str  # pass | logged | warned | blocked | error
    model: str
    latency_ms: int
    scores: dict[str, float] = field(default_factory=dict)
    triggered: dict[str, str] = field(default_factory=dict)
    message: str | None = None
    user_proceeded: bool = False

    @property
    def block_message(self) -> str | None:
        return self.message if self.decision == "blocked" else None

    @property
    def pending_warning(self) -> bool:
        """A warning the user has not answered yet, so one to show."""
        return self.decision == "warned" and not self.user_proceeded

    def as_record(self) -> dict:
        """JSON-serializable form stored under Turn.guardrail."""
        record = {
            "model": self.model,
            "latency_ms": self.latency_ms,
            "decision": self.decision,
            "scores": self.scores,
            "triggered": self.triggered,
        }
        if self.decision == "warned":
            # Whether people send anyway is the number that decides if 'warn'
            # earns its place, so it only makes sense on a warning.
            record["user_proceeded"] = self.user_proceeded
        return record


def _message_for(categories: set[str]) -> str:
    if "selfharm" in categories:
        return SELF_HARM_MESSAGE
    if categories == {"pii"}:
        return PII_MESSAGE
    return GENERIC_MESSAGE


def _verdict(
    check: PromptCheck, scores: dict[str, float], latency_ms: int
) -> CheckResult:
    triggered = check.triggered(scores)
    action = check.action_for(scores)
    decision = _DECISIONS[action]
    # Only the categories asking for the strongest action explain the decision,
    # so a category merely logged never picks the message.
    deciding = {c for c, a in triggered.items() if a == action}

    return CheckResult(
        decision=decision,
        model=check.model,
        latency_ms=latency_ms,
        # Every category, not just the ones that triggered. Prompts that hide in
        # a never-acted-on category are the known weakness of this classifier,
        # and dropping those scores would make them invisible.
        scores=dict(scores),
        triggered=triggered,
        message=(_message_for(deciding) if decision in ("blocked", "warned") else None),
    )


def _count_failure(failed: bool) -> None:
    """Track consecutive moderation failures so a dark check stays visible.

    Read back by `utils.database.prompt_checks.get_consecutive_failures`.
    """
    try:
        client = get_redis_client()
        if failed:
            client.incr(REDIS_CHECK_FAILURES_KEY)
        else:
            client.delete(REDIS_CHECK_FAILURES_KEY)
    except Exception as e:
        logger.error(f"[CHECKS] Error updating failure count: {e}")


def count_warning_shown() -> None:
    """Count one warning put in front of a user.

    Read back by `utils.database.prompt_checks.get_warnings_shown`. The turns
    carry `user_proceeded` only when the user sent anyway, so this count is what
    that number is measured against.
    """
    try:
        get_redis_client().incr(REDIS_CHECK_WARNINGS_KEY)
    except Exception as e:
        logger.error(f"[CHECKS] Error counting warning: {e}")


def _read_cache(text: str) -> dict[str, float] | None:
    """Scores already computed for this exact prompt, if any."""
    try:
        raw = get_redis_client().get(
            REDIS_CHECK_SCORES_KEY.format(hash=hash_content(text))
        )
    except Exception as e:
        logger.warning(f"[CHECKS] Error reading cached scores: {e}")
        return None

    if not raw:
        return None

    try:
        return {category: float(v) for category, v in json.loads(str(raw)).items()}
    except (TypeError, ValueError) as e:
        logger.warning(f"[CHECKS] Error decoding cached scores: {e}")
        return None


def _write_cache(text: str, scores: dict[str, float]) -> None:
    try:
        get_redis_client().setex(
            REDIS_CHECK_SCORES_KEY.format(hash=hash_content(text)),
            SCORES_TTL,
            json.dumps(scores),
        )
    except Exception as e:
        logger.warning(f"[CHECKS] Error caching scores: {e}")


async def run_prompt_check(
    text: str, request: "Request | None" = None, proceed: bool = False
) -> CheckResult | None:
    """
    Check a user prompt with one moderation call, or None when nothing ran.

    The caller refuses the prompt when `result.block_message` is set, asks the
    user to confirm when `result.pending_warning` is true, and otherwise
    persists `result.as_record()` on the turn.

    The scores of a prompt that warned are kept for `SCORES_TTL` seconds, so
    the second call made when the user sends it anyway reuses them instead of
    paying for another moderation call. The verdict is recomputed from the
    current configuration either way, so an admin who tightens a category while
    a warning is on screen still gets the new behaviour. `proceed` marks the
    warning as answered.
    """
    if not settings.MISTRAL_API_KEY:
        return None

    check = await get_prompt_check()
    if not check.is_enabled:
        return None

    started = time.monotonic()
    cached = _read_cache(text)

    if cached is not None:
        scores, latency_ms = cached, 0
    else:
        try:
            scores = await moderate(text, check.model)
        except Exception as e:
            latency_ms = int((time.monotonic() - started) * 1000)
            logger.error(f"prompt_check_failed: {e}", extra={"request": request})
            if settings.SENTRY_DSN:
                sentry_sdk.capture_exception(e)
            _count_failure(failed=True)
            return CheckResult(
                decision="error", model=check.model, latency_ms=latency_ms
            )

        latency_ms = int((time.monotonic() - started) * 1000)
        _count_failure(failed=False)

    result = _verdict(check, scores, latency_ms)

    if result.decision == "warned":
        if cached is None:
            _write_cache(text, scores)
        result.user_proceeded = proceed

    logger.info(
        f"prompt_check_verdict: {result.as_record()}", extra={"request": request}
    )
    return result
