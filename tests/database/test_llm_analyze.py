"""
Unit tests for Config.analyze_comparison's error handling: a single
unanalyzable comparison must never take down the worker processing it.

    uv run pytest tests/database/test_llm_analyze.py
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import litellm  # noqa: E402

from utils.database.actions.llm_analyze import (  # noqa: E402
    AnalysisModel,
    Config,
    LLMAnalysisFailed,
)
from utils.database.models.comparison import (  # noqa: E402
    Comparison,
    ComparisonLLMAnalysisFailedUpdate,
    ComparisonLLMAnalysisUpdate,
)

# The package exports a function of the same name, which shadows the module.
llm_analyze = sys.modules["utils.database.actions.llm_analyze"]


def moderation_block() -> litellm.exceptions.APIError:
    """What a provider content-moderation block surfaces as, e.g. Gemini's
    PROHIBITED_CONTENT or OpenRouter's own prompt-injection filter."""
    return litellm.exceptions.APIError(
        status_code=403,
        message="Gemini blocked the request: PROHIBITED_CONTENT",
        llm_provider="openrouter",
        model="google/gemini-flash",
    )


def comparison() -> Comparison:
    return Comparison(
        ip="127.0.0.1", mode="random", llm_id_a=uuid.uuid4(), llm_id_b=uuid.uuid4()
    )


def analyzer() -> Config:
    config = Config(AnalysisModel(model="openrouter/x", api_base=None, api_key="k"))
    # Config.failed_analysis is a class-level default shared across instances;
    # give each test its own list so results don't leak between tests.
    config.failed_analysis = []
    return config


def run_with(monkeypatch, outcomes: list):
    """
    Drive analyze_comparison with a scripted sequence of _analyze() outcomes
    (exceptions to raise, or a ComparisonLLMAnalysisUpdate to return), one per
    call, in order.
    """
    calls = []

    async def fake_analyze(self, prompt):
        calls.append(prompt)
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    updates = []

    async def fake_update_comparison(comparison_id, data):
        updates.append((comparison_id, data))

    monkeypatch.setattr(Config, "_analyze", fake_analyze)
    monkeypatch.setattr(llm_analyze, "update_comparison", fake_update_comparison)

    config = analyzer()
    comp = comparison()
    exc = None
    try:
        asyncio.run(config.analyze_comparison(comp))
    except Exception as e:
        exc = e
    return config, comp, updates, exc, len(calls)


def test_exhausted_provider_error_marks_failed_and_keeps_worker_alive(monkeypatch):
    config, comp, updates, exc, call_count = run_with(
        monkeypatch, [moderation_block()] * (Config.MAX_RETRIES + 1)
    )

    assert exc is None, f"analyze_comparison should not raise, raised {exc!r}"
    assert call_count == Config.MAX_RETRIES + 1
    assert len(updates) == 1
    updated_id, data = updates[0]
    assert updated_id == comp.id
    assert isinstance(data, ComparisonLLMAnalysisFailedUpdate)
    assert str(comp.id) in config.failed_analysis


def test_exhausted_bad_llm_response_marks_failed_same_as_before(monkeypatch):
    config, comp, updates, exc, call_count = run_with(
        monkeypatch, [LLMAnalysisFailed("bad json")] * (Config.MAX_RETRIES + 1)
    )

    assert exc is None
    assert call_count == Config.MAX_RETRIES + 1
    assert len(updates) == 1
    assert isinstance(updates[0][1], ComparisonLLMAnalysisFailedUpdate)
    assert str(comp.id) in config.failed_analysis


def test_unexpected_error_still_propagates(monkeypatch):
    config, comp, updates, exc, call_count = run_with(
        monkeypatch, [RuntimeError("bug")]
    )

    assert isinstance(exc, RuntimeError)
    assert call_count == 1
    assert updates == []
    assert config.failed_analysis == []


def test_transient_provider_error_then_success_is_recorded_as_analyzed(monkeypatch):
    success = ComparisonLLMAnalysisUpdate(
        contains_pii=False,
        contains_spam=False,
        short_summary="a short summary",
        keywords=[],
        categories=[],
        languages=["en"],
    )
    config, comp, updates, exc, call_count = run_with(
        monkeypatch, [moderation_block(), success]
    )

    assert exc is None
    assert call_count == 2
    assert len(updates) == 1
    updated_id, data = updates[0]
    assert updated_id == comp.id
    assert data is success
    assert config.failed_analysis == []


def run_pipeline(monkeypatch, total: int, analyze):
    """Wire analyze_comparisons to a fake DB stream of `total` comparisons and
    the given analyze_comparison; returns the list counting comparisons produced."""
    produced = []

    async def fake_stream(_filters):
        for _ in range(total):
            produced.append(1)
            yield comparison()

    async def fake_model():
        return AnalysisModel(model="openrouter/x", api_base=None, api_key="k")

    monkeypatch.setattr(llm_analyze, "get_db_comparisons_stream", fake_stream)
    monkeypatch.setattr(llm_analyze, "get_analysis_model", fake_model)
    monkeypatch.setattr(Config, "analyze_comparison", analyze)
    return produced


def test_backlog_is_not_loaded_in_memory_faster_than_workers_consume_it(monkeypatch):
    total = 200
    seen_while_blocked = []

    async def scenario():
        gate = asyncio.Event()

        async def analyze(self, comp):
            await gate.wait()

        produced = run_pipeline(monkeypatch, total, analyze)
        task = asyncio.create_task(llm_analyze.analyze_comparisons())
        await asyncio.sleep(0.2)
        seen_while_blocked.append(len(produced))
        gate.set()
        await asyncio.wait_for(task, timeout=5)
        return len(produced)

    assert asyncio.run(scenario()) == total
    assert seen_while_blocked[0] <= Config.WORKERS + Config.QUEUE_SIZE + 1


def test_a_crashing_worker_does_not_hang_the_run(monkeypatch):
    async def scenario():
        async def analyze(self, comp):
            raise RuntimeError("bug")

        run_pipeline(monkeypatch, 200, analyze)
        await asyncio.wait_for(llm_analyze.analyze_comparisons(), timeout=5)

    asyncio.run(scenario())
