"""
Prompt checks run before a user message reaches the arena models.

Two checks, `content_safety` and `pii`, configured in the `prompt_check` table
by an admin. Both are served by a single call to the Mistral moderation API,
which scores eleven categories between 0 and 1, so the runner calls Mistral once
and derives both verdicts from the same scores.

Each check has its own mode: `off` (not run), `log` (verdict stored only),
`warn` (the user is asked to confirm) and `block` (the prompt is refused).

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
from utils.database.prompt_checks import get_prompt_checks
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
class CheckVerdict:
    """Result of one check on one prompt. Persisted on the Turn and logged."""

    kind: str
    mode: str
    decision: str  # pass | logged | warned | blocked | error
    scores: dict[str, float]
    model: str
    latency_ms: int
    categories: list[str] = field(default_factory=list)
    message: str | None = None
    user_proceeded: bool = False

    def as_record(self) -> dict:
        """JSON-serializable form stored under Turn.guardrail[kind]."""
        record = {
            "mode": self.mode,
            "decision": self.decision,
            "scores": self.scores,
            "model": self.model,
            "latency_ms": self.latency_ms,
        }
        if self.decision == "warned":
            # Whether people send anyway is the number that decides if 'warn'
            # earns its place, so it only makes sense on a warning.
            record["user_proceeded"] = self.user_proceeded
        return record


@dataclass
class ChecksResult:
    """Verdicts of every check that ran on one prompt."""

    verdicts: list[CheckVerdict] = field(default_factory=list)

    @property
    def block_message(self) -> str | None:
        for verdict in self.verdicts:
            if verdict.decision == "blocked":
                return verdict.message
        return None

    @property
    def warnings(self) -> list[CheckVerdict]:
        return [v for v in self.verdicts if v.decision == "warned"]

    @property
    def pending_warnings(self) -> list[CheckVerdict]:
        """Warnings the user has not answered yet, so the ones to show."""
        return [v for v in self.warnings if not v.user_proceeded]

    def as_record(self) -> dict | None:
        """Turn.guardrail payload, or None when no check ran."""
        if not self.verdicts:
            return None
        return {verdict.kind: verdict.as_record() for verdict in self.verdicts}


def _message_for(kind: str, categories: list[str]) -> str:
    if kind == "pii":
        return PII_MESSAGE
    return SELF_HARM_MESSAGE if "selfharm" in categories else GENERIC_MESSAGE


def _verdict(
    check: PromptCheck, scores: dict[str, float], model: str, latency_ms: int
) -> CheckVerdict:
    categories = check.blocking_categories(scores)
    if not categories:
        decision = "pass"
    elif check.mode == "block":
        decision = "blocked"
    elif check.mode == "warn":
        decision = "warned"
    else:
        decision = "logged"

    return CheckVerdict(
        kind=check.kind,
        mode=check.mode,
        decision=decision,
        # Every category, not just the ones with a threshold. Prompts that hide
        # in a never-blocking category are the known weakness of this
        # classifier, and dropping those scores would make them invisible.
        scores=dict(scores),
        model=model,
        latency_ms=latency_ms,
        categories=categories,
        message=(
            _message_for(check.kind, categories)
            if decision in ("blocked", "warned")
            else None
        ),
    )


def _error_verdict(check: PromptCheck, latency_ms: int) -> CheckVerdict:
    return CheckVerdict(
        kind=check.kind,
        mode=check.mode,
        decision="error",
        scores={},
        model=check.model,
        latency_ms=latency_ms,
    )


def _count_failure(kind: str, failed: bool) -> None:
    """Track consecutive moderation failures so a dark check stays visible.

    Read back by `utils.database.prompt_checks.get_consecutive_failures`.
    """
    key = REDIS_CHECK_FAILURES_KEY.format(kind=kind)
    try:
        client = get_redis_client()
        if failed:
            client.incr(key)
        else:
            client.delete(key)
    except Exception as e:
        logger.error(f"[CHECKS] Error updating failure count for '{kind}': {e}")


def count_warning_shown(kind: str) -> None:
    """Count one warning put in front of a user.

    Read back by `utils.database.prompt_checks.get_warnings_shown`. The turns
    carry `user_proceeded` only when the user sent anyway, so this count is what
    that number is measured against.
    """
    try:
        get_redis_client().incr(REDIS_CHECK_WARNINGS_KEY.format(kind=kind))
    except Exception as e:
        logger.error(f"[CHECKS] Error counting warning for '{kind}': {e}")


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


async def run_prompt_checks(
    text: str, request: "Request | None" = None, proceed: bool = False
) -> ChecksResult:
    """
    Run every enabled check on a user prompt with one moderation call.

    The caller refuses the prompt when `result.block_message` is set, asks the
    user to confirm when `result.pending_warnings` is not empty, and otherwise
    persists `result.as_record()` on the turn.

    The scores of a prompt that warned are kept for `SCORES_TTL` seconds, so
    the second call made when the user sends it anyway reuses them instead of
    paying for another moderation call. Verdicts are recomputed from the current
    rows either way, so an admin who tightens a check while a warning is on
    screen still gets the new behaviour. `proceed` marks warnings as answered.
    """
    if not settings.MISTRAL_API_KEY:
        return ChecksResult()

    checks = [check for check in await get_prompt_checks() if check.mode != "off"]
    if not checks:
        return ChecksResult()

    # One call for both checks. If the rows disagree on the model, content
    # safety wins rather than paying for a second call, and the row order from
    # the database does not decide it.
    model = next(
        (check.model for check in checks if check.kind == "content_safety"),
        checks[0].model,
    )
    started = time.monotonic()
    cached = _read_cache(text)

    if cached is not None:
        scores, latency_ms = cached, 0
    else:
        try:
            scores = await moderate(text, model)
        except Exception as e:
            latency_ms = int((time.monotonic() - started) * 1000)
            logger.error(f"prompt_check_failed: {e}", extra={"request": request})
            if settings.SENTRY_DSN:
                sentry_sdk.capture_exception(e)
            for check in checks:
                _count_failure(check.kind, failed=True)
            return ChecksResult([_error_verdict(check, latency_ms) for check in checks])

        latency_ms = int((time.monotonic() - started) * 1000)
        for check in checks:
            _count_failure(check.kind, failed=False)

    result = ChecksResult(
        [_verdict(check, scores, model, latency_ms) for check in checks]
    )

    if result.warnings and cached is None:
        _write_cache(text, scores)

    if proceed:
        for verdict in result.warnings:
            verdict.user_proceeded = True

    logger.info(
        f"prompt_check_verdicts: {result.as_record()}", extra={"request": request}
    )
    return result
