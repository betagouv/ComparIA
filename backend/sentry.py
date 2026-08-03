import logging
import os
from typing import Any
from urllib.parse import urlsplit

import sentry_sdk
from sentry_sdk.types import Event

from backend.config import settings
from backend.logger import SAFE_VALUE_PATTERN, exception_metadata

logger = logging.getLogger("languia")

# The only keys allowed out of the process. Numbers pass as they are, strings
# only when SAFE_VALUE_PATTERN says they are an identifier and not free text.
_SAFE_EXTRA_KEYS = frozenset(
    {
        "annotation_count",
        "comparison_id",
        "custom_annotation_chars",
        "custom_model_count",
        "error_code",
        "event",
        "exception_type",
        "generation_id",
        "mode",
        "model",
        "model_id",
        "output_tokens",
        "position",
        "prompt_chars",
        "provider",
        "response_chars",
        "status_code",
        "vote_kind",
        "web_search",
    }
)


def _safe_operational_extra(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    source = value.get("extra") if isinstance(value.get("extra"), dict) else value
    safe: dict[str, Any] = {}
    for key in _SAFE_EXTRA_KEYS:
        item = source.get(key)
        # bool is a subclass of int, so counters and flags both land here.
        if isinstance(item, int) or (
            isinstance(item, str) and SAFE_VALUE_PATTERN.fullmatch(item)
        ):
            safe[key] = item
    return safe


def scrub_sensitive_event(event: Event, _hint: dict[str, Any]) -> Event:
    """Remove request content and free-text values before sending to Sentry."""
    event.pop("user", None)
    event.pop("message", None)
    safe_extra = _safe_operational_extra(event.get("extra"))
    exc_info = _hint.get("exc_info")
    if isinstance(exc_info, tuple) and len(exc_info) > 1:
        exc = exc_info[1]
        if isinstance(exc, BaseException):
            safe_extra.update(
                {
                    key: value
                    for key, value in exception_metadata(exc).items()
                    if key in {"exception_type", "status_code", "error_code"}
                }
            )
    if safe_extra:
        event["extra"] = safe_extra
    else:
        event.pop("extra", None)
    request = event.get("request")
    if isinstance(request, dict):
        for key in ("data", "cookies", "query_string", "headers", "env"):
            request.pop(key, None)
        if isinstance(request.get("url"), str):
            url = urlsplit(request["url"])
            request["url"] = url.path

    for breadcrumb in event.get("breadcrumbs", {}).get("values", []):
        if isinstance(breadcrumb, dict):
            breadcrumb.pop("data", None)
            breadcrumb.pop("message", None)

    exception = event.get("exception")
    if isinstance(exception, dict):
        for value in exception.get("values", []):
            if not isinstance(value, dict):
                continue
            if value.get("value"):
                value["value"] = value.get("type", "Application error")
            for frame in value.get("stacktrace", {}).get("frames", []):
                if isinstance(frame, dict):
                    frame.pop("vars", None)

    for span in event.get("spans", []):
        if isinstance(span, dict):
            span.pop("data", None)
            span.pop("description", None)

    logentry = event.get("logentry")
    if isinstance(logentry, dict):
        # "formatted" and "params" carry the interpolated log arguments. Keep
        # "message", the template, so issues still have a readable title.
        logentry.pop("formatted", None)
        logentry.pop("params", None)

    return event


def init_sentry() -> None:
    if not settings.SENTRY_DSN:
        logger.debug("Will not init Sentry: no SENTRY_DSN env variable found")
        return

    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    sentry_sdk.init(
        release=settings.GIT_COMMIT,
        attach_stacktrace=True,
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_SAMPLE_RATE,
        profiles_sample_rate=settings.SENTRY_SAMPLE_RATE,
        project_root=os.getcwd(),
        send_default_pii=False,
        max_request_body_size="never",
        before_send=scrub_sensitive_event,
        before_send_transaction=scrub_sensitive_event,
        include_local_variables=False,
    )
    logger.debug(
        "Sentry loaded with traces_sample_rate="
        + str(settings.SENTRY_SAMPLE_RATE)
        + " and profiles_sample_rate="
        + str(settings.SENTRY_SAMPLE_RATE)
        + " for release "
        + str(settings.GIT_COMMIT)
    )
