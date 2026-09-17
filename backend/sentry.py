import logging
import os
from typing import Any

import sentry_sdk

from backend.config import settings
from backend.logger import redact_invite_token

logger = logging.getLogger("languia")

# Keys that can carry a user prompt or model output, stripped from every
# event/breadcrumb before it leaves the process.
_SENSITIVE_KEYS = {"messages", "prompt", "content", "api_key"}


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: (None if k in _SENSITIVE_KEYS else _scrub(v)) for k, v in value.items()
        }
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


def _before_send(event: dict, hint: dict) -> dict:
    # Requests bodies/headers can contain prompts, cookies or auth tokens.
    request = event.get("request", {})
    request.pop("data", None)
    request.pop("headers", None)
    # The invite token is a path segment, so it shows up in the request url of
    # errors and transactions alike. Transaction names use the route template,
    # except for paths no route matched.
    if isinstance(request.get("url"), str):
        request["url"] = redact_invite_token(request["url"])
    if isinstance(event.get("transaction"), str):
        event["transaction"] = redact_invite_token(event["transaction"])
    for breadcrumb in event.get("breadcrumbs", {}).get("values", []):
        if "data" in breadcrumb:
            breadcrumb["data"] = _scrub(breadcrumb["data"])
    event["extra"] = _scrub(event.get("extra", {}))
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
        # Frame locals hold the provider endpoint, api_key included, whenever a
        # completion raises. Sentry's own scrubber only looks at top-level
        # variable names, so it would send the key through.
        include_local_variables=False,
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_SAMPLE_RATE,
        profiles_sample_rate=settings.SENTRY_SAMPLE_RATE,
        project_root=os.getcwd(),
        send_default_pii=False,
        before_send=_before_send,
        before_send_transaction=_before_send,
    )
    logger.debug(
        "Sentry loaded with traces_sample_rate="
        + str(settings.SENTRY_SAMPLE_RATE)
        + " and profiles_sample_rate="
        + str(settings.SENTRY_SAMPLE_RATE)
        + " for release "
        + str(settings.GIT_COMMIT)
    )
