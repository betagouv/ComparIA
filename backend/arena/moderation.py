"""
Content-safety guardrail for user prompts.

Sends the user message to NVIDIA Nemotron 3.5 Content Safety (Aegis 2.0 taxonomy)
via OpenRouter and decides whether a small set of egregious categories should be
blocked before any arena model is called. Everything else passes through.

Two independent switches (careful rollout):
- GUARDRAIL_ENABLED: run the check, log + persist the verdict (shadow mode).
- GUARDRAIL_ENFORCE: actually block. When False, the verdict is observed only
  and the prompt always proceeds.

Fails open: if the guardrail errors or times out, the prompt is allowed (this is
a comparison tool, not a hard gate). Fail-open is NOT fail-silent: failures are
logged at error level and sent to Sentry so a dark guard is visible.

Model output looks like:
    User Safety: safe
    User Safety: unsafe\nSafety Categories: Guns and Illegal Weapons, Criminal Planning/Confessions
"""

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import litellm
import sentry_sdk

from backend.config import settings
from backend.logger import exception_metadata

if TYPE_CHECKING:
    from fastapi import Request

logger = logging.getLogger("languia")

# French refusals (platform default locale). No em dashes.
_GENERIC = (
    "Votre message n'a pas pu être envoyé car il enfreint nos conditions "
    "d'utilisation. Veuillez le reformuler."
)
_SELF_HARM = (
    "Si vous traversez une période difficile ou avez des pensées suicidaires, "
    "vous n'êtes pas seul·e. Le 3114, numéro national de prévention du suicide, "
    "est joignable gratuitement et de façon confidentielle 24h/24 et 7j/7."
)

# Keywords matched against the lowercased category line. Punctuation in the
# emitted labels is unstable ("Guns and Illegal Weapons" vs "Guns/Illegal
# Weapons"), so we match on stable substrings rather than exact category names.
_OTHER_BLOCK_KEYWORDS = ("weapon", "criminal planning", "controlled", "hate", "sexual")


@dataclass
class GuardrailVerdict:
    """Result of one guardrail check. Persisted on the Turn and logged."""

    safety: str  # "safe" | "unsafe" | "error"
    categories: list[str]
    block_message: str | None  # French refusal if egregious, else None
    enforced: bool  # whether GUARDRAIL_ENFORCE was on for this check
    model: str
    latency_ms: int | None = None

    @property
    def should_block(self) -> bool:
        """Block only when enforcing AND the prompt hit an egregious category."""
        return self.enforced and self.block_message is not None

    def as_record(self) -> dict:
        """JSON-serializable form stored on Turn.guardrail."""
        return {
            "safety": self.safety,
            "categories": self.categories,
            "blocked": self.block_message is not None,  # would-block (egregious)
            "enforced": self.enforced,
            "model": self.model,
            "latency_ms": self.latency_ms,
        }


def classify(content: str) -> str | None:
    """
    Decide whether a Nemotron verdict should block. Returns the French refusal
    message to show the user, or None to allow. Pure function (no network) so it
    can be unit-tested against recorded model outputs.
    """
    text = content.lower()
    if "unsafe" not in text:
        return None

    # CSAM ("Sexual (minor)") always blocks, no Needs Caution override.
    if "minor" in text:
        return _GENERIC

    # Self-harm always shows the 3114 prevention line, exempt from the Needs
    # Caution veto: missing a flagged suicide prompt is worse than occasionally
    # showing the resource on a false positive.
    if "suicide" in text or "self harm" in text or "self-harm" in text:
        return _SELF_HARM

    # Needs Caution is the model's own hedge flag: suppress blocks on the
    # borderline cases (e.g. violent fiction, harm-reduction drug talk).
    if "needs caution" in text:
        return None

    if any(k in text for k in _OTHER_BLOCK_KEYWORDS):
        return _GENERIC

    return None


def _categories(content: str) -> list[str]:
    """Parse the 'Safety Categories: a, b' line into a list (best effort)."""
    if "Safety Categories:" not in content:
        return []
    tail = content.split("Safety Categories:", 1)[1]
    return [c.strip() for c in tail.replace("\n", " ").split(",") if c.strip()]


async def check_prompt(
    text: str, request: "Request | None" = None
) -> GuardrailVerdict | None:
    """
    Run the guardrail on a user prompt. Returns a GuardrailVerdict (for logging
    and persistence) or None when the guardrail is disabled / unconfigured.

    The caller blocks only when `verdict.should_block` is True; otherwise the
    prompt proceeds and the verdict is recorded for observability.

    This is a synchronous pre-check, so it adds the guardrail's latency before
    streaming starts. If that becomes a problem it can run concurrently with the
    model streams and abort on a block, since the prompt is known up front.
    """
    if not settings.GUARDRAIL_ENABLED or not settings.OPENROUTER_API_KEY:
        return None

    started = time.monotonic()

    try:
        response = await litellm.acompletion(
            model=settings.GUARDRAIL_MODEL,
            api_key=settings.OPENROUTER_API_KEY,
            messages=[{"role": "user", "content": text}],
            stream=False,
            timeout=settings.GUARDRAIL_TIMEOUT,
            max_tokens=128,
            # Disable THINK mode: we want the terse "User Safety: ..." verdict in
            # content, not a chain-of-thought that overflows max_tokens.
            reasoning={"enabled": False},
        )
        content = response.choices[0].message.content or ""
    except Exception as e:
        # Fail open, but make it visible: a dark guard must not be silent.
        logger.error(
            "Guardrail check failed",
            extra={
                "request": request,
                "extra": {
                    "event": "guardrail.failed",
                    "model": settings.GUARDRAIL_MODEL,
                    **exception_metadata(e),
                },
            },
        )
        if settings.SENTRY_DSN:
            sentry_sdk.capture_exception(
                e,
                extras={
                    "event": "guardrail.failed",
                    "model": settings.GUARDRAIL_MODEL,
                },
            )
        return GuardrailVerdict(
            safety="error",
            categories=[],
            block_message=None,
            enforced=settings.GUARDRAIL_ENFORCE,
            model=settings.GUARDRAIL_MODEL,
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    verdict = GuardrailVerdict(
        safety="unsafe" if "unsafe" in content.lower() else "safe",
        categories=_categories(content),
        block_message=classify(content),
        enforced=settings.GUARDRAIL_ENFORCE,
        model=settings.GUARDRAIL_MODEL,
        latency_ms=int((time.monotonic() - started) * 1000),
    )
    logger.info(f"guardrail_verdict: {verdict.as_record()}", extra={"request": request})
    return verdict
