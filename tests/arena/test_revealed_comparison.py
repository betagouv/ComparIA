"""
Once a comparison is revealed, the visitor knows which model is which: no new
turn, retry or vote may reach the ranking after that (no DB, no Redis).

Run with pytest, or directly:
    uv run python tests/arena/test_revealed_comparison.py
"""

import asyncio
import inspect
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

import backend.arena.router as arena_router  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router


def test_a_revealed_comparison_is_refused():
    with pytest.raises(HTTPException) as raised:
        asyncio.run(
            arena_router.get_unrevealed_comparison(SimpleNamespace(revealed=True))
        )
    assert raised.value.status_code == 403
    assert raised.value.detail == "comparison_revealed"


def test_a_blind_comparison_goes_through():
    comparison = SimpleNamespace(revealed=False)
    assert asyncio.run(arena_router.get_unrevealed_comparison(comparison)) is comparison


@pytest.mark.parametrize("route", ["add_text", "retry", "vote"])
def test_routes_that_reach_the_ranking_ask_for_a_blind_comparison(route):
    annotations = [
        parameter.annotation
        for parameter in inspect.signature(
            getattr(arena_router, route)
        ).parameters.values()
    ]
    assert arena_router.UnrevealedComparisonAnno in annotations


if __name__ == "__main__":
    test_a_revealed_comparison_is_refused()
    test_a_blind_comparison_goes_through()
    for route in ["add_text", "retry", "vote"]:
        test_routes_that_reach_the_ranking_ask_for_a_blind_comparison(route)
    print("ok")
