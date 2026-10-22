"""
The check run on a user prompt before it reaches the arena models.

An admin writes the criteria in the `prompt_check` table: a yes/no question
about the prompt, what counts as yes and as no, a threshold and an action. A
decision model on OpenRouter answers every criterion in one call with the
probability of yes, read next to a description of the instance. The actions
are `off` (never triggers), `log` (verdict stored only), `warn` (the user is
asked to confirm) and `block` (the prompt is refused). A prompt takes the
strongest action any triggered criterion asks for.

A prompt is not sent as one input. A short request buried in a long harmless
text comes out diluted, and a long input is slow enough to run past the
timeout. The prompt is cut into overlapping windows, scored again in a folded
spelling (look-alike letters, leetspeak, invisible characters) and with any
encoded part decoded, and a criterion takes its highest score over all of
them. On a follow-up, the end of the previous user messages joined to the
start of the new one is scored too, so a request split across turns is seen
whole. That reading can only ask the user to confirm, never refuse.

When the model is down (OUTAGE_AFTER_FAILURES failures in a row), the check
pauses for OUTAGE_PAUSE_SECONDS and every prompt goes through as `skipped`,
charged to no one. While it is up and the check is `required`, nothing reaches
the models unchecked: a prompt whose check fails is refused, and so are web
search results. When it is not, both go through and the failure is recorded. Being rate
limited does not count toward the pause, so the check cannot be switched off by
flooding us, and neither does OpenRouter refusing our key or running out of
credits: a required check refuses every prompt until that is fixed.
Failures are logged at error level, sent to Sentry, and counted in Redis so the
admin panel shows a check that has stopped working.
"""

import asyncio
import contextlib
import json
import logging
import secrets
import time
from typing import TYPE_CHECKING, Final, NamedTuple, Sequence

import httpx
import sentry_sdk

from backend.arena.normalize import decoded_variants, fold
from backend.config import settings
from utils.database.encrypted import UnreadableRow, UnreadableSecret
from utils.database.models.prompt_check import (
    PromptCheck,
    PromptCheckResult,
    strongest_action,
)
from utils.database.prompt_checks import get_prompt_check
from utils.secrets import SecretUnreadableError
from utils.storage.redis import (
    REDIS_CHECK_CALLS_KEY,
    REDIS_CHECK_FAILURES_KEY,
    REDIS_CHECK_KEY_REJECTED_KEY,
    REDIS_CHECK_NO_CREDITS_KEY,
    REDIS_CHECK_PAUSED_KEY,
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

DECISIONS_URL: Final[str] = "https://openrouter.ai/api/alpha/decisions"
DECISION_MODELS_URL: Final[str] = "https://openrouter.ai/api/v1/models"
# Per request. A failed request is tried once more. Calls took 0.4s typically
# and 1.1s at worst on our bench.
DECISION_TIMEOUT: Final[float] = 4.0
# For the whole check of one prompt, waiting for a free call included.
CHECK_DEADLINE: Final[float] = 12.0
# The most calls one prompt may cost, follow-up context included: eight rounds
# of four. An ordinary prompt at the length limit needs 7, twice that when its
# folded spelling differs; one that unfolds into far more text (some
# characters fold into eighteen) is not sent at all.
# Over it with the earlier turns only, those are left unread instead.
MAX_CHECK_CALLS: Final[int] = 32
# The longest a rate limited call waits before its one retry, whatever
# Retry-After asks for: the deadline above still caps the whole check.
RATE_LIMIT_WAIT: Final[float] = 2.0
# How long cached scores stay reusable, i.e. how long the user has to read the
# warning and decide.
SCORES_TTL: Final[int] = 900

# Window size and overlap. Any passage up to CHUNK_OVERLAP characters long
# falls whole inside at least one window.
CHUNK_CHARS: Final[int] = 8_000
CHUNK_OVERLAP: Final[int] = 400
# Calls in flight on this instance, across all requests: OpenRouter answered 429
# to six at once on our bench. A slot lapses after SLOT_LEASE_SECONDS, so a
# worker that dies holding one does not shrink the pool for good. It outlives
# the deadline, which cancels every call of a check: a live call never loses
# its slot, whatever httpx's per-read timeout lets a slow answer take.
PARALLEL_CALLS: Final[int] = 4
SLOT_LEASE_SECONDS: Final[float] = CHECK_DEADLINE + 3
SLOT_WAIT_SECONDS: Final[float] = 0.05
# How many earlier user messages a follow-up is scored with.
CONTEXT_TURNS: Final[int] = 4

# Failures in a row after which the model counts as down, and how long the check
# then pauses before trying again. Being rate limited (429) is not counted:
# our own traffic causes it, an attacker's included, and it must not be a way
# to switch the check off.
OUTAGE_AFTER_FAILURES: Final[int] = 5
OUTAGE_PAUSE_SECONDS: Final[int] = 60
# OpenRouter refusing our key is not an outage either: it is ours to fix, and
# pausing would let every message through unchecked until someone noticed.
KEY_REJECTED_STATUS = frozenset({401, 403})
# Out of credits, on the account or the key's own limit: the provider is up,
# our budget is not, so this is not an outage either.
NO_CREDITS_STATUS = 402

_TRANSIENT_STATUS = frozenset({429, 500, 502, 503, 504})

# Keys, not sentences: see PromptCheckMessage.
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
    """Every window of every spelling of the prompt worth scoring.

    The decoded parts are read as one text, not one call each: six hundred
    short base64 blobs would otherwise cost six hundred calls. Their windows
    then grow with the prompt's length, like the others, and nothing is left
    unread.
    """
    spellings = [text]
    folded = fold(text)
    if folded.split() != text.split():
        spellings.append(folded)
    if decoded := decoded_variants(text):
        spellings.append("\n\n".join(decoded))
    return list(dict.fromkeys(c for spelling in spellings for c in chunks(spelling)))


def context_inputs(text: str, context: Sequence[str]) -> tuple[list[str], list[str]]:
    """
    The end of the earlier user messages joined to the start of this one, and
    that same end alone, to tell what the new message added.
    """
    earlier = [message for message in context[-CONTEXT_TURNS:] if message]
    if not earlier:
        return [], []
    tail = "\n\n".join(earlier)[-CHUNK_CHARS:]
    joined = tail + "\n\n" + text[:CHUNK_CHARS]
    return moderation_inputs(joined), moderation_inputs(tail)


class Scores(NamedTuple):
    """Highest score per criterion: for the prompt alone, for the prompt read
    after the earlier messages, and for the earlier messages alone. The last
    two stay empty on a first message."""

    own: dict[str, float]
    joined: dict[str, float] = {}
    earlier: dict[str, float] = {}


def highest(scores: Sequence[dict[str, float]]) -> dict[str, float]:
    merged: dict[str, float] = {}
    for one in scores:
        for key, score in one.items():
            merged[key] = max(score, merged.get(key, 0.0))
    return merged


async def list_decision_models() -> list[dict[str, str]]:
    """The decision models OpenRouter lists, as `id` and `name`.

    Empty when OpenRouter cannot be reached: the admin field still takes any
    id typed in, so the page works without the list.
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                DECISION_MODELS_URL, params={"output_modalities": "decisions"}
            )
            response.raise_for_status()
            models = response.json()["data"]
    except (httpx.HTTPError, KeyError, ValueError) as e:
        logger.warning(f"[CHECKS] Cannot list decision models: {e}")
        return []
    return [{"id": m["id"], "name": m.get("name") or m["id"]} for m in models]


def questions(check: PromptCheck) -> dict[str, dict]:
    """One yes/no question per criterion that can act, keyed on the criterion."""
    asked = {}
    for c in check.active_criteria:
        question: dict = {"type": "noul", "instructions": c["question"]}
        if c["yes"] and c["no"]:
            question["criteria"] = {"true": c["yes"], "false": c["no"]}
        elif c["yes"] or c["no"]:
            question["instructions"] += (
                f" Oui : {c['yes']}" if c["yes"] else f" Non : {c['no']}"
            )
        asked[c["key"]] = question
    return asked


async def _post(
    client: httpx.AsyncClient,
    text: str,
    check: PromptCheck,
    api_key: str,
) -> dict[str, float]:
    asked = questions(check)
    for attempt in (1, 2):
        try:
            response = await client.post(
                DECISIONS_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": check.model,
                    "state": {"plateforme": check.description, "message": text},
                    "questions": asked,
                },
            )
        except httpx.TransportError:
            if attempt == 2:
                raise
            continue
        if response.status_code in _TRANSIENT_STATUS and attempt == 1:
            if response.status_code == 429:
                await asyncio.sleep(_retry_after(response))
            continue
        response.raise_for_status()
        break

    answers = response.json()["answers"]
    missing = set(asked) - set(answers)
    if missing:
        raise ValueError(f"No answer for {', '.join(sorted(missing))}")
    return {key: float(answers[key]["noul"]) for key in asked}


class CheckOverloaded(Exception):
    """Our own limit ran out, not the provider: the check missed its deadline,
    or the prompt would cost more than MAX_CHECK_CALLS calls.

    Never counted toward the outage pause, which only a failing provider may
    open: otherwise enough traffic at once would switch a required check off.
    """


def _retry_after(response: httpx.Response) -> float:
    """How long a 429 asks us to wait, within RATE_LIMIT_WAIT."""
    try:
        wait = float(response.headers.get("retry-after", 1))
    except ValueError:
        wait = 1.0
    return min(max(wait, 0.0), RATE_LIMIT_WAIT)


async def _take_slot(key: str, stamp: str) -> bool:
    """Wait for one of the PARALLEL_CALLS slots of this key. False when Redis
    cannot say, and the call goes on held by this request's own limit only."""
    while True:
        try:
            now = time.time()
            pipe = get_redis_client().pipeline()
            pipe.zremrangebyscore(key, 0, now)
            pipe.zadd(key, {stamp: now + SLOT_LEASE_SECONDS})
            pipe.zcard(key)
            pipe.expire(key, int(SLOT_LEASE_SECONDS) + 1)
            count = pipe.execute()[2]
            if count <= PARALLEL_CALLS:
                return True
            get_redis_client().zrem(key, stamp)
        except Exception as e:
            logger.warning(f"[CHECKS] Cannot share the call limit: {e}")
            return False
        await asyncio.sleep(SLOT_WAIT_SECONDS)


@contextlib.asynccontextmanager
async def _slot(key: str):
    stamp = secrets.token_hex(8)
    taken = False
    try:
        taken = await _take_slot(key, stamp)
        yield
    finally:
        if taken:
            try:
                get_redis_client().zrem(key, stamp)
            except Exception as e:
                logger.warning(f"[CHECKS] Cannot free a call slot: {e}")


async def moderate_many(
    inputs: list[str], check: PromptCheck, api_key: str | UnreadableSecret
) -> list[dict[str, float]]:
    """Scores for each input, in order, a few calls at a time.

    At most PARALLEL_CALLS calls are in flight on this instance, whoever makes
    them, and the whole lot must finish within CHECK_DEADLINE, or it raises
    CheckOverloaded.

    A stored key no configured encryption key opens is a failed call, not a
    missing key: the env key is not tried in its place, and the callers count
    the failure like any other so the panel shows the check unhealthy.
    """
    if isinstance(api_key, UnreadableSecret):
        # The configuration is a single row, id 1.
        raise SecretUnreadableError(
            UnreadableRow(PromptCheck.__tablename__, 1, "api_key").message()
        )
    gate = asyncio.Semaphore(PARALLEL_CALLS)
    try:
        async with (
            asyncio.timeout(CHECK_DEADLINE),
            httpx.AsyncClient(timeout=DECISION_TIMEOUT) as client,
        ):

            async def one(text: str) -> dict[str, float]:
                async with gate, _slot(REDIS_CHECK_CALLS_KEY):
                    return await _post(client, text, check, api_key)

            # A task group, not gather: on the deadline it cancels every call
            # and waits for each to free its slot before the check returns.
            # The first failing call stands for the check, so the caller still
            # reads its HTTP status.
            try:
                async with asyncio.TaskGroup() as group:
                    tasks = [group.create_task(one(text)) for text in inputs]
            except ExceptionGroup as failed:
                raise failed.exceptions[0] from None
            return [task.result() for task in tasks]
    except TimeoutError as e:
        raise CheckOverloaded(f"No answer within {CHECK_DEADLINE}s") from e


async def moderate(
    text: str,
    check: PromptCheck,
    api_key: str | UnreadableSecret,
    context: Sequence[str] = (),
) -> Scores:
    """Score a prompt over every window and spelling of it, and, given the
    earlier user messages in `context`, read together with them."""
    own = moderation_inputs(text)
    if len(own) > MAX_CHECK_CALLS:
        raise CheckOverloaded(f"{len(own)} calls, over {MAX_CHECK_CALLS}")
    joined, earlier = context_inputs(text, context)
    if len(own) + len(joined) + len(earlier) > MAX_CHECK_CALLS:
        # The earlier turns alone can push a follow-up over: refusing it would
        # refuse every later message of the conversation. That reading can
        # only warn, so it is the one to go, and the message is still scored.
        logger.warning("[CHECKS] Earlier turns over the call budget, not read")
        joined, earlier = [], []
    scores = await moderate_many(own + joined + earlier, check, api_key)
    split = len(own) + len(joined)
    return Scores(
        highest(scores[: len(own)]),
        highest(scores[len(own) : split]),
        highest(scores[split:]),
    )


def context_hits(check: PromptCheck, scores: Scores) -> dict[str, str]:
    """
    Criteria set to `block` that the new message pushes over their threshold
    once read after the earlier ones, each mapped to `warn`.

    A warning, not a block: two harmless messages can read worse side by side,
    and a person can say so. The earlier messages alone must stay under the
    threshold, so an exchange already let through does not warn again on every
    later turn.
    """
    return {
        c["key"]: "warn"
        for c in check.criteria
        if c["action"] == "block"
        and scores.joined.get(c["key"], 0.0) >= c["threshold"]
        and scores.earlier.get(c["key"], 0.0) < c["threshold"]
    }


def _message_for(check: PromptCheck, keys: set[str]) -> str:
    messages = {c["message"] for c in check.criteria if c["key"] in keys}
    if SELF_HARM_MESSAGE in messages:
        return SELF_HARM_MESSAGE
    if messages == {PII_MESSAGE}:
        return PII_MESSAGE
    return GENERIC_MESSAGE


def verdict(check: PromptCheck, scores: Scores, latency_ms: int) -> PromptCheckResult:
    """Scores plus a configuration to a decision. Writes nothing, so the admin
    dry run gets the same answer the arena would give without the side effects."""
    triggered = check.triggered(scores.own)
    for key, action in context_hits(check, scores).items():
        triggered.setdefault(key, action)
    action = strongest_action(triggered.values())
    decision = _DECISIONS[action]
    # Only the criteria asking for the strongest action explain the decision,
    # so a criterion merely logged never picks the message.
    deciding = {c for c, a in triggered.items() if a == action}

    return PromptCheckResult(
        decision=decision,
        model=check.model,
        latency_ms=latency_ms,
        # Every criterion asked, not just the ones that triggered, so a prompt
        # that scores just under a threshold stays visible.
        scores=dict(scores.own),
        triggered=triggered,
        message=(
            _message_for(check, deciding) if decision in ("blocked", "warned") else None
        ),
    )


def _count_failure(failed: bool) -> bool:
    """
    Track consecutive check failures so a dark check stays visible, and pause
    the check once there are enough of them to call the model down.

    Read back by `utils.database.prompt_checks.get_consecutive_failures`.

    Returns:
        bool: True when the model counts as down
    """
    try:
        client = get_redis_client()
        if not failed:
            client.delete(REDIS_CHECK_FAILURES_KEY)
            client.delete(REDIS_CHECK_KEY_REJECTED_KEY)
            client.delete(REDIS_CHECK_NO_CREDITS_KEY)
            return False
        count = int(client.incr(REDIS_CHECK_FAILURES_KEY))
        if count < OUTAGE_AFTER_FAILURES:
            return False
        # Once the pause runs out the streak is still there, so the first
        # failure after it pauses again; one success clears both.
        if client.set(REDIS_CHECK_PAUSED_KEY, "1", nx=True, ex=OUTAGE_PAUSE_SECONDS):
            logger.error(
                f"[CHECKS] The decision model failed {count} times in a row, prompt check "
                f"paused for {OUTAGE_PAUSE_SECONDS}s"
            )
        return True
    except Exception as e:
        logger.error(f"[CHECKS] Error updating failure count: {e}")
        return False


def _flag(key: str) -> None:
    """Flag the key for the admin panel: rejected, or out of credits. Read back
    by `utils.database.prompt_checks.is_key_rejected` and `is_out_of_credits`."""
    try:
        get_redis_client().set(key, "1")
    except Exception as e:
        logger.error(f"[CHECKS] Error flagging {key}: {e}")


def is_paused() -> bool:
    try:
        return bool(get_redis_client().exists(REDIS_CHECK_PAUSED_KEY))
    except Exception as e:
        logger.error(f"[CHECKS] Error reading the pause: {e}")
        return False


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


def _scores_cache_key(text: str, check: PromptCheck, context: Sequence[str]) -> str:
    keyed = "\x00".join([text, *context[-CONTEXT_TURNS:]])
    # Scores answer the questions asked, not the thresholds or actions, so
    # moving a threshold keeps them while rewording a criterion does not.
    asked = json.dumps([check.model, check.description, questions(check)])
    return REDIS_CHECK_SCORES_KEY.format(
        model_hash=hash_content(asked), prompt_hash=hash_content(keyed)
    )


def read_cached_scores(
    text: str, check: PromptCheck, context: Sequence[str] = ()
) -> Scores | None:
    """Scores already computed for this exact prompt and context, if any."""
    try:
        raw = get_redis_client().get(_scores_cache_key(text, check, context))
    except Exception as e:
        logger.warning(f"[CHECKS] Error reading cached scores: {e}")
        return None

    if not raw:
        return None

    try:
        data = json.loads(str(raw))
        parts = data if "own" in data else {"own": data}
        return Scores(
            **{
                part: {key: float(v) for key, v in values.items()}
                for part, values in parts.items()
            }
        )
    except (TypeError, ValueError, AttributeError) as e:
        logger.warning(f"[CHECKS] Error decoding cached scores: {e}")
        return None


def write_cached_scores(
    text: str,
    check: PromptCheck,
    scores: Scores,
    context: Sequence[str] = (),
) -> None:
    try:
        get_redis_client().setex(
            _scores_cache_key(text, check, context),
            SCORES_TTL,
            json.dumps(scores._asdict()),
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
    Check a user prompt with the decision model, or None when nothing ran.

    The caller refuses the prompt when `result.block_message` is set, asks the
    user to confirm when `result.pending_warning` is true, and otherwise
    persists `result.as_record()` on the turn.

    The scores of a prompt that warned are kept for `SCORES_TTL` seconds, so
    the second call made when the user sends it anyway reuses them instead of
    paying for another check. The verdict is recomputed from the
    current configuration either way, so an admin who tightens a criterion while
    a warning is on screen still gets the new behaviour. A valid one-time
    `warning_token` marks the warning as answered.

    `context` holds the earlier user messages of the conversation, oldest
    first.
    """
    check = await get_prompt_check()
    if not check.should_run:
        return None

    api_key = check.api_key or settings.OPENROUTER_API_KEY
    if not api_key:
        return None

    if is_paused():
        return PromptCheckResult(decision="skipped", model=check.model, latency_ms=0)

    started = time.monotonic()
    cached = read_cached_scores(text, check, context)

    if cached is not None:
        scores, latency_ms = cached, 0
    else:
        try:
            scores = await moderate(text, check, api_key, context)
        except Exception as e:
            latency_ms = int((time.monotonic() - started) * 1000)
            logger.error(f"prompt_check_failed: {e}", extra={"request": request})
            if settings.SENTRY_DSN:
                sentry_sdk.capture_exception(e)
            status_code = (
                e.response.status_code if isinstance(e, httpx.HTTPStatusError) else None
            )
            if status_code in KEY_REJECTED_STATUS:
                _flag(REDIS_CHECK_KEY_REJECTED_KEY)
            elif status_code == NO_CREDITS_STATUS:
                _flag(REDIS_CHECK_NO_CREDITS_KEY)
            elif (
                status_code != 429
                and not isinstance(e, CheckOverloaded)
                and _count_failure(failed=True)
            ):
                return PromptCheckResult(
                    decision="skipped", model=check.model, latency_ms=latency_ms
                )
            # Without a message the error refuses nothing: the prompt goes
            # through and the failure still shows in the stats.
            return PromptCheckResult(
                decision="error",
                model=check.model,
                latency_ms=latency_ms,
                message=UNAVAILABLE_MESSAGE if check.required else None,
            )

        latency_ms = int((time.monotonic() - started) * 1000)
        _count_failure(failed=False)

    acknowledged = consume_warning_token(text, check.model, warning_token)
    result = verdict(check, scores, latency_ms)

    if result.decision == "warned":
        if cached is None:
            write_cached_scores(text, check, scores, context)
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
    Drop the web search results that would trip a criterion set to `block`.

    Their text goes to the models next to the prompt, so a page written to
    instruct the model is a prompt injection the user never had to type. They
    arrive already cut by `keep_search_results`, so all the models will read is
    scored. If they cannot be scored they are all dropped and the prompt goes
    without them, unless the check is not `required`; they are kept unchecked
    while the model counts as down.

    They share the calls of the prompts: past MAX_CHECK_CALLS, the results
    left are dropped unread rather than delay the prompts of everyone else.
    """
    check = await get_prompt_check()
    api_key = check.api_key or settings.OPENROUTER_API_KEY
    if not check.should_run or not api_key or is_paused():
        return results

    per_result = []
    for result in results:
        inputs = moderation_inputs(result.content or "")
        if sum(map(len, per_result)) + len(inputs) > MAX_CHECK_CALLS:
            logger.warning(
                f"[CHECKS] {len(results) - len(per_result)} web search result(s) "
                "over the call budget, dropped"
            )
            results = results[: len(per_result)]
            break
        per_result.append(inputs)
    try:
        scores = await moderate_many(
            [i for inputs in per_result for i in inputs], check, api_key
        )
    except Exception as e:
        if not check.required:
            logger.error(f"[CHECKS] Web search results not checked, kept: {e}")
            return results
        logger.error(f"[CHECKS] Web search results not checked, dropped: {e}")
        return []

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
