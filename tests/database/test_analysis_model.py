"""
Unit tests for resolving the model comparison analysis runs on (no DB).

    uv run pytest tests/database/test_analysis_model.py
"""

import asyncio
import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from utils.database.actions.llm_analyze import (  # noqa: E402
    AnalysisNotConfigured,
    get_analysis_model,
)
from utils.database.models.app_settings import AppSettings  # noqa: E402
from utils.database.models.llms import LLMEndpoint  # noqa: E402

# The package exports a function of the same name, which shadows the module.
llm_analyze = sys.modules["utils.database.actions.llm_analyze"]

ENDPOINT_ID = uuid.UUID("9667ee84-9b07-4d3d-890c-57fc9ffe9c33")


def resolve(monkeypatch, app_settings: AppSettings, endpoint: LLMEndpoint | None):
    async def fake_settings():
        return app_settings

    class FakeSession:
        async def get(self, _model, _id):
            return endpoint

    @asynccontextmanager
    async def fake_session():
        yield FakeSession()

    monkeypatch.setattr(llm_analyze, "get_app_settings", fake_settings)
    monkeypatch.setattr(llm_analyze, "get_session", fake_session)
    return asyncio.run(get_analysis_model())


def openrouter(api_key: str | None = "sk-or-x") -> LLMEndpoint:
    return LLMEndpoint(
        id=ENDPOINT_ID, name="OpenRouter", api_type="openrouter", api_key=api_key
    )


def configured() -> AppSettings:
    return AppSettings(
        id=1, analysis_endpoint_id=ENDPOINT_ID, analysis_model="google/gemini-flash"
    )


def test_the_endpoint_and_the_model_become_one_litellm_model(monkeypatch):
    analysis = resolve(monkeypatch, configured(), openrouter())
    assert analysis.model == "openrouter/google/gemini-flash"
    assert analysis.api_base is None
    assert analysis.api_key == "sk-or-x"


def refuses(monkeypatch, app_settings, endpoint) -> str:
    try:
        resolve(monkeypatch, app_settings, endpoint)
    except AnalysisNotConfigured as exc:
        return str(exc)
    raise AssertionError("expected the analysis to refuse to run")


def test_analysis_refuses_to_run_half_configured(monkeypatch):
    # Nothing set at all: the setting has never been filled in.
    assert "admin panel" in refuses(monkeypatch, AppSettings(id=1), openrouter())
    # An endpoint chosen but no model, which would send an empty model name.
    assert "admin panel" in refuses(
        monkeypatch,
        AppSettings(id=1, analysis_endpoint_id=ENDPOINT_ID),
        openrouter(),
    )
    # The endpoint was deleted after being chosen.
    assert "gone" in refuses(monkeypatch, configured(), None)
    # An endpoint with no key answers 401 on every comparison in the queue.
    assert "no API key" in refuses(monkeypatch, configured(), openrouter(api_key=None))
