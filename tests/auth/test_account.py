"""
Unit tests for the account settings endpoints (no DB, no Redis).

Run with pytest, or directly:
    uv run python tests/auth/test_account.py
"""

import asyncio
import contextlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import backend.auth.router as auth_router  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router


@contextlib.contextmanager
def patched(module, **attributes):
    originals = {name: getattr(module, name) for name in attributes}
    for name, value in attributes.items():
        setattr(module, name, value)
    try:
        yield
    finally:
        for name, value in originals.items():
            setattr(module, name, value)


def test_public_config_carries_the_deployment_url():
    """The accessibility declaration names the domain it applies to."""

    async def get_app_settings():
        return SimpleNamespace(
            auth_access_policy="anonymous_first",
            auth_domain_allowlist=[],
            platform_name="Arène de test",
            logo=None,
        )

    with patched(auth_router, get_app_settings=get_app_settings):
        with patched(
            auth_router.settings, COMPARIA_APP_URL="https://arene.example.test"
        ):
            config = asyncio.run(auth_router.get_config())

    assert config.platform_url == "https://arene.example.test"


if __name__ == "__main__":
    for name, test in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            test()
