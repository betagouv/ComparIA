"""What the model health test reports, for a model that answers and for each way one fails."""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import litellm
import pytest

from backend.admin.llms import health, router
from backend.errors import EmptyResponseError

LLM = SimpleNamespace(id="llm-id")


def stream_of(*parts: str, error: Exception | None = None):
    async def stream(msg, **_):
        for part in parts:
            msg.content += part
            yield msg
        if error:
            raise error

    return stream


def run(monkeypatch, stream):
    monkeypatch.setattr(health, "litellm_stream_iter", stream)
    return asyncio.run(health.check_llm_health(LLM))


def test_a_model_that_answers_is_healthy_with_its_latency(monkeypatch):
    result = run(monkeypatch, stream_of("", "OK"))
    assert result.healthy
    assert result.latency_ms is not None
    assert result.error is None


def test_it_stops_reading_at_the_first_token(monkeypatch):
    result = run(monkeypatch, stream_of("OK", error=RuntimeError("read too far")))
    assert result.healthy


def test_a_reasoning_token_counts_as_an_answer(monkeypatch):
    async def stream(msg, **_):
        msg.reasoning_content = "thinking"
        yield msg

    assert run(monkeypatch, stream).healthy


def test_a_model_that_says_nothing_is_unhealthy(monkeypatch):
    result = run(monkeypatch, stream_of("", ""))
    assert not result.healthy
    assert result.error == "empty_response"


@pytest.mark.parametrize(
    "error, code",
    [
        (litellm.Timeout("slow", "model", "openrouter"), "timeout"),
        (TimeoutError(), "timeout"),
        (EmptyResponseError(), "empty_response"),
        (litellm.AuthenticationError("no", "openrouter", "model"), "key_rejected"),
        (litellm.RateLimitError("no", "openrouter", "model"), "rate_limited"),
        (litellm.NotFoundError("no", "model", "openrouter"), "model_not_found"),
        (RuntimeError("boom"), "provider_error"),
    ],
)
def test_each_failure_gets_its_code_and_no_provider_text(monkeypatch, error, code):
    result = run(monkeypatch, stream_of(error=error))
    assert result.model_dump() == {
        "healthy": False,
        "latency_ms": None,
        "error": code,
    }


def test_a_402_means_out_of_credits(monkeypatch):
    error = RuntimeError("payment required")
    error.status_code = 402
    assert run(monkeypatch, stream_of(error=error)).error == "no_credits"


def test_an_enabled_model_without_a_usable_key_is_not_configured(monkeypatch):
    async def no_enabled_models():
        return SimpleNamespace(enabled={})

    monkeypatch.setattr(router, "get_llms_data", no_enabled_models)
    result = asyncio.run(router.test_llm_health(uuid4()))
    assert result.model_dump() == {
        "healthy": False,
        "latency_ms": None,
        "error": "not_configured",
    }
