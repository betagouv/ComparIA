"""
A model set to go without the arena's tools: a specialised system that brings
its own retrieval behind its endpoint. It is called without tools on every
path, while the model it faces keeps them, and the dataset says it had none.
"""

import asyncio
import contextlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, AsyncGenerator

import litellm
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

# isort: off
# Before the arena modules, whose imports go round in a circle otherwise.
import utils.database.models  # noqa: E402,F401

# isort: on
import backend.arena.services as services  # noqa: E402
import backend.arena.streaming as streaming  # noqa: E402
from utils.database.models import LLMMessageCreate  # noqa: E402

TOOLS = ["web_search"]


def comparison(llm_a: str, llm_b: str, turns: int = 1) -> Any:
    return SimpleNamespace(
        id="comparison",
        turns=[
            SimpleNamespace(llm_msg_a=None, llm_msg_b=None, user_msg=None)
            for _ in range(turns)
        ],
        llm_id_a=llm_a,
        llm_id_b=llm_b,
        system_msg_a=None,
        system_msg_b=None,
        mode="random",
        custom_models_selection=None,
        enabled_tools=TOOLS,
        error=None,
    )


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[list[str] | None]]:
    """
    Models 'system' and 'spare' bring their own tools, 'generalist' does not.
    'stuck' times out on its first word. Returns, per model, the tools each
    call was handed.
    """
    flags = {"system": False, "generalist": True, "spare": False, "stuck": True}
    seen: dict[str, list[list[str] | None]] = {name: [] for name in flags}

    async def bot_response_async(
        pos, llm, turn, turn_index, messages, request=None, tools=None
    ) -> AsyncGenerator[LLMMessageCreate]:
        seen[llm.id].append([tool.name for tool in tools] if tools else None)
        msg = LLMMessageCreate()
        msg.content = "réponse"
        yield msg
        if llm.id == "stuck":
            raise litellm.Timeout(message="slow", model="stuck", llm_provider="openai")

    async def get_llms_data():
        return SimpleNamespace(
            enabled={
                name: SimpleNamespace(
                    id=name,
                    endpoint=SimpleNamespace(api_type="openai"),
                    arena_tools=flag,
                )
                for name, flag in flags.items()
            }
        )

    async def resolve_tools(keys):
        return [SimpleNamespace(name=key) for key in keys]

    async def pick_replacement_model(_comparison, _pos, charged=False):
        return "spare"

    async def update_comparison_llm_id(comparison, pos, llm_id):
        setattr(comparison, f"llm_id_{pos}", llm_id)

    async def update_comparison_error(_comparison, _error):
        return None

    monkeypatch.setattr(streaming, "bot_response_async", bot_response_async)
    monkeypatch.setattr(streaming, "get_llms_data", get_llms_data)
    monkeypatch.setattr(streaming, "resolve_tools", resolve_tools)
    monkeypatch.setattr(streaming, "pick_replacement_model", pick_replacement_model)
    monkeypatch.setattr(streaming, "update_comparison_llm_id", update_comparison_llm_id)
    monkeypatch.setattr(streaming, "update_comparison_error", update_comparison_error)
    return seen


def stream(current: Any) -> list[Any]:
    async def collect():
        return [
            event
            async for event in streaming.stream_comparison_messages(
                current, current.turns[-1]
            )
        ]

    return asyncio.run(collect())


def test_the_first_turn_gives_tools_to_one_side_only(calls):
    stream(comparison("system", "generalist"))
    assert calls["system"] == [None]
    assert calls["generalist"] == [TOOLS]


def test_a_later_turn_and_a_retry_keep_it_that_way(calls):
    later = comparison("generalist", "system", turns=3)
    stream(later)
    # A retry streams the same comparison again, from the same stored tools.
    stream(later)
    assert calls["system"] == [None, None]
    assert calls["generalist"] == [TOOLS, TOOLS]


def test_a_replacement_that_brings_its_own_tools_gets_none(calls):
    events = stream(comparison("generalist", "stuck"))
    assert {"type": "swap", "pos": "b"} in events
    assert calls["stuck"] == [TOOLS]
    assert calls["spare"] == [None]
    assert calls["generalist"] == [TOOLS]


@pytest.mark.parametrize(
    "flags, rejects, expected",
    [
        # The default: both sides take tools.
        ((True, True), False, {"a": True, "b": True}),
        ((False, True), False, {"a": False, "b": True}),
        # Same outcome as a model whose provider refused the tools.
        ((True, True), True, {"a": False, "b": False}),
    ],
)
def test_the_dataset_records_the_side_that_had_no_tools(
    monkeypatch, flags, rejects, expected
):
    row = SimpleNamespace(tool_capable_a=None, tool_capable_b=None)

    async def get_llms_data():
        return SimpleNamespace(
            enabled={
                name: SimpleNamespace(
                    arena_tools=flag,
                    litellm_endpoint=SimpleNamespace(model=f"openai/{name}"),
                )
                for name, flag in zip(("x", "y"), flags)
            }
        )

    @contextlib.asynccontextmanager
    async def get_session():
        async def commit():
            return None

        yield SimpleNamespace(add=lambda _row: None, commit=commit)

    async def get_item(_cls, _id, _session):
        return row

    monkeypatch.setattr(services, "get_llms_data", get_llms_data)
    monkeypatch.setattr(services, "get_session", get_session)
    monkeypatch.setattr(services, "_get_item", get_item)
    monkeypatch.setattr(services, "model_rejects_tools", lambda _model: rejects)

    asyncio.run(services.update_comparison_tool_capability(comparison("x", "y")))
    assert {"a": row.tool_capable_a, "b": row.tool_capable_b} == expected
