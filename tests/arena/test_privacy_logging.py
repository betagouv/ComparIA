import json
import logging
import sys
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import Request

from backend.logger import JSONFormatter, exception_metadata
from backend.sentry import scrub_sensitive_event
from backend.utils.user import get_matomo_tracker_from_cookies

COMPARISON_ID = "59aa09e4-e75d-45f9-8209-586b1d0d237d"


class ProviderError(RuntimeError):
    status_code = 429
    code = "rate_limit_exceeded"


def test_sentry_scrubber_removes_free_text_and_request_identifiers():
    event = {
        "request": {
            "method": "POST",
            "url": "https://example.test/arena/add_first_text?secret=query",
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
                    "stacktrace": {
                        "frames": [
                            {
                                "filename": "backend/arena/streaming.py",
                                "function": "stream_llm_response",
                                "lineno": 150,
                                "vars": {"prompt": "secret"},
                            }
                        ]
                    },
                }
            ]
        },
        "logentry": {"message": "Provider failed", "params": ["secret prompt"]},
        "extra": {
            "extra": {
                "event": "arena.model_response_failed",
                "model_id": "model-1",
                "comparison_id": COMPARISON_ID,
                "prompt": "secret prompt",
                "response": "secret response",
            }
        },
        "spans": [{"description": "secret query", "data": {"prompt": "secret"}}],
    }

    error = ProviderError("secret provider response")
    scrubbed = scrub_sensitive_event(
        event, {"exc_info": (ProviderError, error, error.__traceback__)}
    )
    serialized = json.dumps(scrubbed)

    assert "secret" not in serialized
    assert scrubbed["request"]["method"] == "POST"
    assert scrubbed["request"]["url"] == "/arena/add_first_text"
    assert scrubbed["exception"]["values"][0]["value"] == "ProviderError"
    assert scrubbed["exception"]["values"][0]["stacktrace"]["frames"] == [
        {
            "filename": "backend/arena/streaming.py",
            "function": "stream_llm_response",
            "lineno": 150,
        }
    ]
    assert scrubbed["extra"] == {
        "event": "arena.model_response_failed",
        "model_id": "model-1",
        "comparison_id": COMPARISON_ID,
        "exception_type": "ProviderError",
        "status_code": 429,
        "error_code": "rate_limit_exceeded",
    }


def test_exception_metadata_keeps_safe_traceback_without_error_content():
    try:
        raise ProviderError("secret provider response")
    except ProviderError as exc:
        details = exception_metadata(exc)

    assert details["exception_type"] == "ProviderError"
    assert details["status_code"] == 429
    assert details["error_code"] == "rate_limit_exceeded"
    assert details["traceback"]
    assert "secret provider response" not in json.dumps(details)


def test_json_logger_keeps_route_metadata_without_request_personal_data():
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/arena/add_first_text",
            "query_string": b"prompt=secret",
            "headers": [
                (b"cookie", b"session=secret"),
                (b"x-comparison-id", COMPARISON_ID.encode()),
            ],
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
    assert payload["comparison_id"] == COMPARISON_ID
    assert "query_params" not in payload
    assert "ip" not in payload
    assert "secret" not in json.dumps(payload)


def test_json_logger_ignores_invalid_comparison_id():
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/arena/comparison",
            "query_string": b"",
            "headers": [(b"x-comparison-id", b"not-a-uuid")],
            "client": ("192.0.2.1", 1234),
            "server": ("example.test", 443),
            "scheme": "https",
            "route": SimpleNamespace(path="/arena/comparison"),
        }
    )
    record = logging.LogRecord("languia", logging.INFO, __file__, 1, "Event", (), None)
    record.request = request

    payload = json.loads(JSONFormatter("%(message)s").format(record))

    assert "comparison_id" not in payload


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


if __name__ == "__main__":
    test_sentry_scrubber_removes_free_text_and_request_identifiers()
    test_exception_metadata_keeps_safe_traceback_without_error_content()
    test_json_logger_keeps_route_metadata_without_request_personal_data()
    test_json_logger_ignores_invalid_comparison_id()
    test_matomo_cookie_identifier_is_not_logged()
