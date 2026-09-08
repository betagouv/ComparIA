"""
What an exception is allowed to carry off the box.

A completion holds the provider endpoint, api_key and all, in its frame. Sentry
attaches frame locals by default and only redacts top-level variable names, so
the key rode along inside `kwargs` and inside the endpoint's repr. This runs the
options we ship against a fake transport and reads what would have been sent.

Run with pytest, or directly:
    uv run python tests/arena/test_sentry_scrubbing.py
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import sentry_sdk  # noqa: E402
from sentry_sdk.transport import Transport  # noqa: E402

import backend.sentry as backend_sentry  # noqa: E402

API_KEY = "sk-a-real-looking-provider-key"


def shipped_options():
    """The kwargs init_sentry() would hand to sentry_sdk.init()."""
    recorded = {}

    def record(**kwargs):
        recorded.update(kwargs)

    with patch.object(backend_sentry.settings, "SENTRY_DSN", "https://k@example.test/1"):
        with patch.object(sentry_sdk, "init", record):
            backend_sentry.init_sentry()
    return recorded


class CapturingTransport(Transport):
    def __init__(self):
        super().__init__({})
        self.events = []

    def capture_envelope(self, envelope):
        for item in envelope.items:
            if item.headers.get("type") == "event":
                self.events.append(item.payload.json)


def event_for_a_failed_completion():
    transport = CapturingTransport()
    options = shipped_options()
    options["transport"] = transport

    def completion():
        kwargs = {"model": "gpt-4o-mini", "api_key": API_KEY}
        raise RuntimeError("provider unreachable: " + kwargs["model"])

    sentry_sdk.init(**options)
    try:
        sentry_sdk.set_extra("endpoint", {"model": "gpt-4o-mini", "api_key": API_KEY})
        try:
            completion()
        except RuntimeError as error:
            sentry_sdk.capture_exception(error)
    finally:
        sentry_sdk.get_client().close()

    assert transport.events, "the client dropped the event before we could read it"
    return json.dumps(transport.events[0], default=str)


def test_a_provider_key_never_reaches_sentry():
    assert API_KEY not in event_for_a_failed_completion()


def test_the_event_still_says_what_broke():
    assert "provider unreachable" in event_for_a_failed_completion()


if __name__ == "__main__":
    test_a_provider_key_never_reaches_sentry()
    test_the_event_still_says_what_broke()
    print("ok")
