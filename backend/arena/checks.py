"""
The check run on a user prompt before it reaches the arena models.

The Mistral moderation API scores eleven categories between 0 and 1. Each
category carries its own threshold and its own action, configured in the
`prompt_check` table by an admin: `off` (never triggers), `log` (verdict stored
only), `warn` (the user is asked to confirm) and `block` (the prompt is
refused). A prompt takes the strongest action any triggered category asks for.

A prompt is not sent as one input. Mistral gives one score to a whole input, so
a short request buried in a long harmless text comes out diluted, and a long
input is slow enough to run past the timeout. The prompt is cut into
overlapping windows, scored again in a folded spelling (look-alike letters,
leetspeak, invisible characters) and with any encoded part decoded, and a
category takes its highest score over all of them. On a follow-up, the end of
the previous user messages joined to the start of the new one is scored too,
so a request split across turns is seen whole.

Fails open for short prompts: if Mistral errors or times out twice, the prompt
proceeds. Fail-open is NOT fail-silent: failures are logged at error level, sent
to Sentry, and counted in Redis so the admin panel can show a check that has
quietly stopped working. They also spend the caller's per-IP block budget (see
`run_checks` in the router). Long prompts fail closed, since length is the
cheap way to make the check time out.
"""

import asyncio
import json
import logging
import secrets
import time
from typing import TYPE_CHECKING, Final, Sequence

import httpx
import sentry_sdk

from backend.arena.normalize import decoded_variants, fold
from backend.config import settings
from utils.database.encrypted import UnreadableRow, UnreadableSecret
from utils.database.models.prompt_check import PromptCheck, PromptCheckResult
from utils.database.prompt_checks import get_prompt_check
from utils.secrets import SecretUnreadableError
from utils.storage.redis import (
    REDIS_CHECK_FAILURES_KEY,
    REDIS_CHECK_SCORES_KEY,
    REDIS_CHECK_WARNING_TOKEN_KEY,
    REDIS_CHECK_WARNINGS_KEY,
    get_redis_client,
    hash_content,
)

if TYPE_CHECKING:
    from fastapi import Request
    from linkup import LinkupSearchTextResult

logger = logging.getLogger("languia")

MISTRAL_MODERATION_URL: Final[str] = "https://api.mistral.ai/v1/moderations"
# Per request. A failed request is tried once more, so a check waits at most
# about twice this.
MODERATION_TIMEOUT: Final[float] = 2.5
# How long cached scores stay reusable, i.e. how long the user has to read the
# warning and decide.
SCORES_TTL: Final[int] = 900

# Window size and overlap. Any passage up to CHUNK_OVERLAP characters long
# falls whole inside at least one window.
CHUNK_CHARS: Final[int] = 2_000
CHUNK_OVERLAP: Final[int] = 400
# Mistral takes a list of inputs per request; batches go out in parallel.
INPUTS_PER_REQUEST: Final[int] = 16
# A prompt longer than one window that could not be checked is refused.
FAIL_CLOSED_ABOVE_CHARS: Final[int] = CHUNK_CHARS
# How many earlier user messages a follow-up is scored with.
CONTEXT_TURNS: Final[int] = 4
# How much of each web search result is read before it goes to the models.
WEB_RESULT_CHARS: Final[int] = 4 * CHUNK_CHARS

_TRANSIENT_STATUS = frozenset({429, 500, 502, 503, 504})

# Keys, not sentences: the frontend picks the wording for the visitor's
# language under `arene.apiErrors.prompt_check`. The self-harm one names a
# helpline, which differs per country, so it cannot live here.
GENERIC_MESSAGE = "generic"
SELF_HARM_MESSAGE = "self_harm"
PII_MESSAGE = "pii"
UNAVAILABLE_MESSAGE = "unavailable"

_DECISIONS = {"off": "pass", "log": "logged", "warn": "warned", "block": "blocked"}


def chunks(text: str) -> list[str]:
    if len(text) <= CHUNK_CHARS:
        return [text]
    step = CHUNK_CHARS - CHUNK_OVERLAP
    return [
        text[start : start + CHUNK_CHARS]
        for start in range(0, len(text) - CHUNK_OVERLAP, step)
    ]


def moderation_inputs(text: str) -> list[str]:
    """Every window of every spelling of the prompt worth scoring."""
    spellings = [text]
    folded = fold(text)
    if folded.split() != text.split():
        spellings.append(folded)
    spellings += decoded_variants(text)
    return list(dict.fromkeys(c for spelling in spellings for c in chunks(spelling)))


def context_inputs(text: str, context: Sequence[str]) -> list[str]:
    """The end of the earlier user messages joined to the start of this one."""
    earlier = [message for message in context[-CONTEXT_TURNS:] if message]
    if not earlier:
        return []
    joined = "\n\n".join(earlier)[-CHUNK_CHARS:] + "\n\n" + text[:CHUNK_CHARS]
    return moderation_inputs(joined)


def highest(scores: Sequence[dict[str, float]]) -> dict[str, float]:
    merged: dict[str, float] = {}
    for one in scores:
        for category, score in one.items():
            merged[category] = max(score, merged.get(category, 0.0))
    return merged


async def _post(
    client: httpx.AsyncClient, inputs: list[str], model: str, api_key: str
) -> list[dict[str, float]]:
    for attempt in (1, 2):
        try:
            response = await client.post(
                MISTRAL_MODERATION_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "input": inputs},
            )
        except httpx.TransportError:
            if attempt == 2:
                raise
            continue
        if response.status_code in _TRANSIENT_STATUS and attempt == 1:
            continue
        response.raise_for_status()
        break

    results = response.json()["results"]
    if len(results) != len(inputs):
        raise ValueError(f"{len(results)} results for {len(inputs)} inputs")
    return [
        {category: float(score) for category, score in r["category_scores"].items()}
        for r in results
    ]


async def moderate_many(
    inputs: list[str], model: str, api_key: str | UnreadableSecret
) -> list[dict[str, float]]:
    """Scores for each input, in order, batched and sent in parallel.

    A stored key no configured encryption key opens is a failed call, not a
    missing key: the env key is not tried in its place, and the callers count
    the failure like any other so the panel shows the check unhealthy.
    """
    if isinstance(api_key, UnreadableSecret):
        # The configuration is a single row, id 1.
        raise SecretUnreadableError(
            UnreadableRow(PromptCheck.__tablename__, 1, "api_key").message()
        )
    batches = [
        inputs[i : i + INPUTS_PER_REQUEST]
        for i in range(0, len(inputs), INPUTS_PER_REQUEST)
    ]
    async with httpx.AsyncClient(timeout=MODERATION_TIMEOUT) as client:
        results = await asyncio.gather(
            *(_post(client, batch, model, api_key) for batch in batches)
        )
    return [scores for batch in results for scores in batch]


async def moderate(
    text: str,
    model: str,
    api_key: str | UnreadableSecret,
    context: Sequence[str] = (),
) -> tuple[dict[str, float], dict[str, float]]:
    """
    Score a prompt: the highest each category reaches over every window and
    spelling of it, and separately over the windows that join it to the
    earlier user messages in `context`.
    """
    own = moderation_inputs(text)
    joined = context_inputs(text, context)
    scores = await moderate_many(own + joined, model, api_key)
    return highest(scores[: len(own)]), highest(scores[len(own) :])


def with_context(
    check: PromptCheck, scores: dict[str, float], context_scores: dict[str, float]
) -> dict[str, float]:
    """
    Fold the scores of the earlier turns into the categories set to `block`.

    Only there: an earlier message the user was warned about and sent anyway
    would otherwise raise the same warning on every later turn.
    """
    merged = dict(scores)
    for category, config in check.categories.items():
        if config["action"] == "block":
            merged[category] = max(
                merged.get(category, 0.0), context_scores.get(category, 0.0)
            )
    return merged


def _message_for(categories: set[str]) -> str:
    if "selfharm" in categories:
        return SELF_HARM_MESSAGE
    if categories == {"pii"}:
        return PII_MESSAGE
    return GENERIC_MESSAGE


def verdict(
    check: PromptCheck, scores: dict[str, float], latency_ms: int
) -> PromptCheckResult:
    """Scores plus a configuration to a decision. Writes nothing, so the admin
    dry run gets the same answer the arena would give without the side effects."""
    triggered = check.triggered(scores)
    action = check.action_for(scores)
    decision = _DECISIONS[action]
    # Only the categories asking for the strongest action explain the decision,
    # so a category merely logged never picks the message.
    deciding = {c for c, a in triggered.items() if a == action}

    return PromptCheckResult(
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


def _scores_cache_key(text: str, model: str, context: Sequence[str]) -> str:
    keyed = "\x00".join([text, *context[-CONTEXT_TURNS:]])
    return REDIS_CHECK_SCORES_KEY.format(
        model_hash=hash_content(model), prompt_hash=hash_content(keyed)
    )


def read_cached_scores(
    text: str, model: str, context: Sequence[str] = ()
) -> dict[str, float] | None:
    """Scores already computed for this exact prompt and context, if any."""
    try:
        raw = get_redis_client().get(_scores_cache_key(text, model, context))
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


def write_cached_scores(
    text: str,
    model: str,
    scores: dict[str, float],
    context: Sequence[str] = (),
) -> None:
    try:
        get_redis_client().setex(
            _scores_cache_key(text, model, context),
            SCORES_TTL,
            json.dumps(scores),
        )
    except Exception as e:
        logger.warning(f"[CHECKS] Error caching scores: {e}")


def issue_warning_token(text: str, model: str) -> str:
    """Return a short-lived, one-time proof that this prompt was warned."""
    token = secrets.token_urlsafe(32)
    get_redis_client().setex(
        REDIS_CHECK_WARNING_TOKEN_KEY.format(token=token),
        SCORES_TTL,
        json.dumps({"prompt_hash": hash_content(text), "model": model}),
    )
    return token


def consume_warning_token(text: str, model: str, token: str | None) -> bool:
    """Accept an acknowledgement only after a matching server warning."""
    if not token:
        return False
    key = REDIS_CHECK_WARNING_TOKEN_KEY.format(token=token)
    try:
        client = get_redis_client()
        expected = client.getdel(key)
    except Exception as e:
        logger.warning(f"[CHECKS] Error consuming warning token: {e}")
        return False
    if not expected:
        return False
    try:
        proof = json.loads(str(expected))
        return secrets.compare_digest(
            proof["prompt_hash"], hash_content(text)
        ) and secrets.compare_digest(proof["model"], model)
    except (KeyError, TypeError, ValueError):
        return False


async def run_prompt_check(
    text: str,
    request: "Request | None" = None,
    warning_token: str | None = None,
    context: Sequence[str] = (),
) -> PromptCheckResult | None:
    """
    Check a user prompt with one moderation call, or None when nothing ran.

    The caller refuses the prompt when `result.block_message` is set, asks the
    user to confirm when `result.pending_warning` is true, and otherwise
    persists `result.as_record()` on the turn.

    The scores of a prompt that warned are kept for `SCORES_TTL` seconds, so
    the second call made when the user sends it anyway reuses them instead of
    paying for another moderation call. The verdict is recomputed from the
    current configuration either way, so an admin who tightens a category while
    a warning is on screen still gets the new behaviour. A valid one-time
    `warning_token` marks the warning as answered.

    `context` holds the earlier user messages of the conversation, oldest
    first.
    """
    check = await get_prompt_check()
    if not check.should_run:
        return None

    api_key = check.api_key or settings.MISTRAL_API_KEY
    if not api_key:
        return None

    started = time.monotonic()
    cached = read_cached_scores(text, check.model, context)

    if cached is not None:
        scores, latency_ms = cached, 0
    else:
        try:
            own, joined = await moderate(text, check.model, api_key, context)
        except Exception as e:
            latency_ms = int((time.monotonic() - started) * 1000)
            logger.error(f"prompt_check_failed: {e}", extra={"request": request})
            if settings.SENTRY_DSN:
                sentry_sdk.capture_exception(e)
            _count_failure(failed=True)
            return PromptCheckResult(
                decision="error",
                model=check.model,
                latency_ms=latency_ms,
                message=(
                    UNAVAILABLE_MESSAGE if len(text) > FAIL_CLOSED_ABOVE_CHARS else None
                ),
            )

        scores = with_context(check, own, joined)
        latency_ms = int((time.monotonic() - started) * 1000)
        _count_failure(failed=False)

    acknowledged = consume_warning_token(text, check.model, warning_token)
    result = verdict(check, scores, latency_ms)

    if result.decision == "warned":
        if cached is None:
            write_cached_scores(text, check.model, scores, context)
        result.user_proceeded = acknowledged

    logger.info(
        f"prompt_check_verdict: {result.model_dump(exclude={'id', 'created_at'})}",
        extra={"request": request},
    )
    return result


async def drop_flagged_results(
    results: "list[LinkupSearchTextResult]",
) -> "list[LinkupSearchTextResult]":
    """
    Drop the web search results that would trip a category set to `block`.

    Their text goes to the models next to the prompt, so a page written to
    instruct the model is a prompt injection the user never had to type. Fails
    open: on error the results are kept, since the prompt itself was checked.
    """
    check = await get_prompt_check()
    api_key = check.api_key or settings.MISTRAL_API_KEY
    if not check.should_run or not api_key:
        return results

    per_result = [
        moderation_inputs((result.content or "")[:WEB_RESULT_CHARS])
        for result in results
    ]
    try:
        scores = await moderate_many(
            [i for inputs in per_result for i in inputs], check.model, api_key
        )
    except Exception as e:
        logger.error(f"[CHECKS] Web search results not checked: {e}")
        return results

    kept = []
    start = 0
    for result, inputs in zip(results, per_result):
        own = highest(scores[start : start + len(inputs)])
        start += len(inputs)
        if check.action_for(own) == "block":
            logger.warning(f"[CHECKS] Dropped flagged web search result {result.url}")
        else:
            kept.append(result)
    return kept
