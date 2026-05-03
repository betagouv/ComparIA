"""Shared test fixtures for tool_arena tests."""

import pytest

from backend.tool_arena.credential import _clear_credential_cache


@pytest.fixture(autouse=True)
def _clear_credential_cache_between_tests():
    """Phase 1 introduced a per-server.id Credential cache. Tests reuse ids
    (e.g. ``test_server``) across different auth shapes, so we clear the
    cache between every test to avoid cross-test contamination."""
    _clear_credential_cache()
    yield
    _clear_credential_cache()
