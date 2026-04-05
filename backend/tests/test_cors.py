"""Unit tests for build_origins() CORS helper."""
from backend.cors_utils import build_origins

_BASE = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:8000",
    "http://localhost:8001",
]


def test_single_extra_origin():
    result = build_origins(_BASE, "https://app.vercel.app")
    assert "https://app.vercel.app" in result
    assert len(result) == len(_BASE) + 1


def test_empty_extra_env_leaves_list_unchanged():
    result = build_origins(_BASE, "")
    assert result == _BASE


def test_unset_extra_env_leaves_list_unchanged():
    result = build_origins(_BASE)
    assert result == _BASE


def test_comma_separated_origins_each_added():
    result = build_origins(_BASE, "https://a.vercel.app, https://b.vercel.app")
    assert "https://a.vercel.app" in result
    assert "https://b.vercel.app" in result
    assert len(result) == len(_BASE) + 2


def test_comma_separated_origins_trimmed():
    result = build_origins(_BASE, "  https://trimmed.app  ")
    assert "https://trimmed.app" in result


def test_base_localhost_origins_always_present():
    result = build_origins(_BASE, "https://extra.app")
    for origin in _BASE:
        assert origin in result
