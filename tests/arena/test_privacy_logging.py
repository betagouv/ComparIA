"""Regression tests for privacy-safe operational telemetry."""

import json
import logging
import sys
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import Request

from backend.logger import JSONFormatter
from backend.sentry import scrub_sensitive_event
from backend.utils.user import get_matomo_tracker_from_cookies


def test_sentry_scrubber_removes_free_text_and_request_identifiers():
    event = {
        "request": {
            "method": "POST",
            "url": "https://example.test/arena/add_first_text",
            "data": {"prompt_value": "secret prompt"},
            "cookies": "session=secret",
            "query_string": "secret=query",
            "headers": {"authorization": "Bearer secret"},
            "env": {"REMOTE_ADDR": "192.0.2.1"},
        },
        "breadcrumbs": {
            "values": [
                {"category": "llm", "message": "secret prompt", "data": {"x": 1}}
            ]
        },
        "exception": {
            "values": [
                {
                    "type": "ProviderError",
                    "value": "secret response",
                    "stacktrace": {"frames": [{"vars": {"prompt": "secret"}}]},
                }
            ]
        },
        "logentry": {"message": "Provider failed", "params": ["secret prompt"]},
        "extra": {"prompt": "secret prompt"},
        "spans": [{"description": "secret query", "data": {"prompt": "secret"}}],
    }

    scrubbed = scrub_sensitive_event(event, {})
    serialized = json.dumps(scrubbed)

    assert "secret" not in serialized
    assert scrubbed["request"]["method"] == "POST"
    assert scrubbed["exception"]["values"][0]["value"] == "ProviderError"


def test_json_logger_keeps_route_metadata_without_request_personal_data():
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/arena/add_first_text",
            "query_string": b"prompt=secret",
            "headers": [(b"cookie", b"session=secret")],
            "client": ("192.0.2.1", 1234),
            "server": ("example.test", 443),
            "scheme": "https",
            "route": SimpleNamespace(path="/arena/add_first_text"),
        }
    )
    record = logging.LogRecord(
        "languia", logging.INFO, __file__, 1, "Arena event", (), None
    )
    record.request = request

    payload = json.loads(JSONFormatter("%(message)s").format(record))

    assert payload["method"] == "POST"
    assert payload["route"] == "/arena/add_first_text"
    assert "query_params" not in payload
    assert "ip" not in payload
    assert "secret" not in json.dumps(payload)


def test_matomo_cookie_identifier_is_not_logged():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("languia")
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        identifier = get_matomo_tracker_from_cookies(
            {"_pk_id.1.example": "secret-visitor-identifier"}
        )
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)

    assert identifier == "secret-visitor-identifier"
    assert "secret-visitor-identifier" not in stream.getvalue()


def run():
    test_sentry_scrubber_removes_free_text_and_request_identifiers()
    test_json_logger_keeps_route_metadata_without_request_personal_data()
    test_matomo_cookie_identifier_is_not_logged()
    print("Privacy logging tests passed.")


if __name__ == "__main__":
    run()
