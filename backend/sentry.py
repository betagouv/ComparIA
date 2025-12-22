import logging
import os

import sentry_sdk

from backend.config import settings

logger = logging.getLogger("languia")


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
        environment=settings.SENTRY_ENV,
        traces_sample_rate=settings.SENTRY_SAMPLE_RATE,
        profiles_sample_rate=settings.SENTRY_SAMPLE_RATE,
        project_root=os.getcwd(),
    )
    logger.debug(
        "Sentry loaded with traces_sample_rate="
        + str(settings.SENTRY_SAMPLE_RATE)
        + " and profiles_sample_rate="
        + str(settings.SENTRY_SAMPLE_RATE)
        + " for release "
        + str(settings.GIT_COMMIT)
    )
