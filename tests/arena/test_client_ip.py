"""
Unit tests for get_ip behind a WAF that puts the real client IP in its own header.

Run with pytest, or directly:
    uv run python tests/arena/test_client_ip.py
"""

import contextlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")

from backend.config import settings
from backend.utils.user import get_ip


def make_request(headers, peer="10.2.0.5"):
    # Starlette headers are case-insensitive; a lowercase dict mimics that here.
    return SimpleNamespace(
        headers={k.lower(): v for k, v in headers.items()},
        client=SimpleNamespace(host=peer),
    )


@contextlib.contextmanager
def configured(header="", hops=0):
    original = (settings.COMPARIA_CLIENT_IP_HEADER, settings.COMPARIA_TRUSTED_PROXY_COUNT)
    settings.COMPARIA_CLIENT_IP_HEADER = header
    settings.COMPARIA_TRUSTED_PROXY_COUNT = hops
    try:
        yield
    finally:
        (
            settings.COMPARIA_CLIENT_IP_HEADER,
            settings.COMPARIA_TRUSTED_PROXY_COUNT,
        ) = original


def test_client_ip_header_wins_over_forwarded_for():
    request = make_request(
        {"X-TCP-IP": "141.94.213.0", "X-Forwarded-For": "213.186.41.196"}
    )
    with configured(header="x-tcp-ip", hops=1):
        assert get_ip(request) == "141.94.213.0"


def test_client_ip_header_is_ignored_when_unset():
    request = make_request({"X-TCP-IP": "141.94.213.0"})
    with configured():
        assert get_ip(request) == "10.2.0.5"


def test_invalid_client_ip_header_falls_back():
    request = make_request(
        {"X-TCP-IP": "not-an-ip", "X-Forwarded-For": "203.0.113.7"}
    )
    with configured(header="x-tcp-ip", hops=1):
        assert get_ip(request) == "203.0.113.7"
    with configured(header="x-tcp-ip"):
        assert get_ip(request) == "10.2.0.5"


def test_missing_client_ip_header_falls_back():
    request = make_request({})
    with configured(header="x-tcp-ip"):
        assert get_ip(request) == "10.2.0.5"


def test_client_ip_header_accepts_ipv6():
    request = make_request({"X-TCP-IP": "2001:db8::1"})
    with configured(header="x-tcp-ip"):
        assert get_ip(request) == "2001:db8::1"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
