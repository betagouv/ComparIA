import asyncio
import logging
from contextlib import aclosing
from time import perf_counter
from typing import Literal

import litellm
from pydantic import BaseModel

from backend.arena.litellm import litellm_stream_iter
from backend.config import ORDBOGEN_STREAM_TIMEOUT
from backend.errors import EmptyResponseError
from backend.llms.models import LLMDataEnabled
from utils.database.models import LLMMessageCreate, UserMessageRead

logger = logging.getLogger("languia")

HEALTH_PROMPT = "Réponds uniquement par le mot : OK"
# The stream closes on the first token. This is only a ceiling, high enough
# for a model that thinks before it writes.
HEALTH_MAX_TOKENS = 256
# Above the slowest stream timeout, so the provider's own timeout fires first.
HEALTH_TIMEOUT = ORDBOGEN_STREAM_TIMEOUT + 5
NO_CREDITS_STATUS = 402

HealthError = Literal[
    "timeout",
    "key_rejected",
    "no_credits",
    "rate_limited",
    "model_not_found",
    "empty_response",
    "provider_error",
    # Marked enabled, but its endpoint has no usable key.
    "not_configured",
]


class LLMHealth(BaseModel):
    healthy: bool
    latency_ms: int | None = None
    error: HealthError | None = None


def _health_error(e: Exception) -> HealthError:
    """A code for the panel. The provider's own message stays in the log."""
    if isinstance(e, (litellm.Timeout, TimeoutError)):
        return "timeout"
    if isinstance(e, EmptyResponseError):
        return "empty_response"
    if getattr(e, "status_code", None) == NO_CREDITS_STATUS:
        return "no_credits"
    if isinstance(e, litellm.AuthenticationError):
        return "key_rejected"
    if isinstance(e, litellm.RateLimitError):
        return "rate_limited"
    if isinstance(e, litellm.NotFoundError):
        return "model_not_found"
    return "provider_error"


async def _first_token(llm: LLMDataEnabled) -> None:
    msg = LLMMessageCreate()
    stream = litellm_stream_iter(
        llm=llm,
        messages=[UserMessageRead(content=HEALTH_PROMPT)],
        msg=msg,
        temperature=0.7,
        max_new_tokens=HEALTH_MAX_TOKENS,
    )
    async with aclosing(stream):
        async for partial in stream:
            if partial.content or partial.reasoning_content:
                return
    raise EmptyResponseError()


async def check_llm_health(llm: LLMDataEnabled) -> LLMHealth:
    """Go through the arena's own call, so a pass means the arena can reach it."""
    start = perf_counter()
    try:
        async with asyncio.timeout(HEALTH_TIMEOUT):
            await _first_token(llm)
    except Exception as e:
        logger.warning(f"llm_health_failed: {llm.id}: {e}")
        return LLMHealth(healthy=False, error=_health_error(e))
    return LLMHealth(healthy=True, latency_ms=round((perf_counter() - start) * 1000))
