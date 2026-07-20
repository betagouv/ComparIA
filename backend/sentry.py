import logging
import os
from typing import Any

import sentry_sdk
from sentry_sdk.types import Event

from backend.config import settings

logger = logging.getLogger("languia")


def scrub_sensitive_event(event: Event, _hint: dict[str, Any]) -> Event:
    """Remove request content and free-text values before sending to Sentry."""
    event.pop("user", None)
    event.pop("message", None)
    event.pop("extra", None)
    request = event.get("request")
    if isinstance(request, dict):
        for key in ("data", "cookies", "query_string", "headers", "env", "url"):
            request.pop(key, None)

    for breadcrumb in event.get("breadcrumbs", {}).get("values", []):
        if isinstance(breadcrumb, dict):
            breadcrumb.pop("data", None)
            breadcrumb.pop("message", None)

    exception = event.get("exception")
    if isinstance(exception, dict):
        for value in exception.get("values", []):
            if isinstance(value, dict) and value.get("value"):
                value["value"] = value.get("type", "Application error")
            if isinstance(value, dict):
                for frame in value.get("stacktrace", {}).get("frames", []):
                    if isinstance(frame, dict):
                        frame.pop("vars", None)

    for span in event.get("spans", []):
        if isinstance(span, dict):
            span.pop("data", None)
            span.pop("description", None)

    logentry = event.get("logentry")
    if isinstance(logentry, dict):
        logentry.pop("params", None)
        logentry["message"] = "Application log event"

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
