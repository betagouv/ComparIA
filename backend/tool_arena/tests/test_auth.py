"""Unit tests for OAuth2 token cache in auth.py."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import backend.tool_arena.auth as auth_module
from backend.tool_arena.config import OAuth2Auth

pytestmark = pytest.mark.anyio


def _make_oauth2_auth(
    client_id: str = "test_id",
    client_secret_env: str = "TEST_SECRET",
    token_url: str = "https://example.com/token",
) -> OAuth2Auth:
    return OAuth2Auth(
        type="oauth2",
        client_id=client_id,
        client_secret_env=client_secret_env,
        token_url=token_url,
    )


def _make_mock_httpx_client(access_token: str = "tok123", expires_in: int = 3600):
    """Build a mock httpx.AsyncClient context manager."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": access_token, "expires_in": expires_in}
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=None)

    return ctx, mock_client


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear token cache before each test for isolation."""
    auth_module._clear_token_cache()
    yield
    auth_module._clear_token_cache()


async def test_get_token_fetches_from_token_url():
    """get_token posts to token_url with client_credentials grant."""
    auth = _make_oauth2_auth()
    ctx, mock_client = _make_mock_httpx_client(access_token="tok123")

    with patch.dict("os.environ", {"TEST_SECRET": "secret_value"}):
        with patch("httpx.AsyncClient", return_value=ctx):
            token = await auth_module.get_token("srv1", auth)

    assert token == "tok123"
    mock_client.post.assert_awaited_once()
    call_args = mock_client.post.call_args
    form_data = call_args.kwargs.get("data") or call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("data", {})
    assert form_data.get("grant_type") == "client_credentials"
    assert form_data.get("client_id") == "test_id"
    assert form_data.get("client_secret") == "secret_value"


async def test_get_token_returns_cached_on_second_call():
    """Second call to get_token returns cached token without re-fetching."""
    auth = _make_oauth2_auth()
    ctx, mock_client = _make_mock_httpx_client(access_token="tok123", expires_in=3600)

    with patch.dict("os.environ", {"TEST_SECRET": "secret_value"}):
        with patch("httpx.AsyncClient", return_value=ctx):
            token1 = await auth_module.get_token("srv1", auth)
            token2 = await auth_module.get_token("srv1", auth)

    assert token1 == "tok123"
    assert token2 == "tok123"
    # httpx.AsyncClient (and thus post) only called once
    assert mock_client.post.await_count == 1


async def test_get_token_refreshes_after_expiry():
    """get_token re-fetches when cached token has expired."""
    auth = _make_oauth2_auth()
    ctx, mock_client = _make_mock_httpx_client(access_token="tok_expired", expires_in=0)

    with patch.dict("os.environ", {"TEST_SECRET": "secret_value"}):
        with patch("httpx.AsyncClient", return_value=ctx):
            await auth_module.get_token("srv1", auth)
            await auth_module.get_token("srv1", auth)

    # Both calls should hit the token endpoint because expires_in=0
    assert mock_client.post.await_count == 2


async def test_get_token_raises_on_missing_env_var():
    """get_token raises KeyError when the env var for the secret is not set."""
    auth = _make_oauth2_auth(client_secret_env="MISSING_SECRET_XYZ")
    ctx, _ = _make_mock_httpx_client()

    import os
    # Ensure it's not set
    os.environ.pop("MISSING_SECRET_XYZ", None)

    with patch("httpx.AsyncClient", return_value=ctx):
        with pytest.raises(KeyError):
            await auth_module.get_token("srv1", auth)


async def test_clear_token_cache():
    """_clear_token_cache empties the cache."""
    auth = _make_oauth2_auth()
    ctx, _ = _make_mock_httpx_client()

    with patch.dict("os.environ", {"TEST_SECRET": "secret_value"}):
        with patch("httpx.AsyncClient", return_value=ctx):
            await auth_module.get_token("srv1", auth)

    assert len(auth_module._token_cache) == 1
    auth_module._clear_token_cache()
    assert len(auth_module._token_cache) == 0
