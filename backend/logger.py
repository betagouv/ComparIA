import datetime
import json
import logging
import os
import queue
import re
import sys
import traceback
import uuid
from logging.handlers import WatchedFileHandler

from fastapi import Request
from logging_loki import LokiQueueHandler as BaseLokiQueueHandler


class LokiHandler(BaseLokiQueueHandler):
    def __init__(self, **kwargs):
        super().__init__(queue=queue.Queue(-1), **kwargs)

    def handleError(self, record: logging.LogRecord) -> None:
        pass


from rich.logging import RichHandler

from backend.config import settings

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Strings only reach logs and Sentry when they look like an identifier. Free text
# is where prompts and model responses hide.
SAFE_VALUE_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}")


def _short_path(filename: str) -> str:
    # Absolute paths expose the deployment layout, so keep them project-relative.
    relative = os.path.relpath(filename, _PROJECT_ROOT)
    return os.path.basename(filename) if relative.startswith("..") else relative


def exception_metadata(exc: BaseException) -> dict[str, object]:
    metadata: dict[str, object] = {
        "exception_type": type(exc).__name__,
        "traceback": [
            {
                "file": _short_path(frame.filename),
                "line": frame.lineno,
                "function": frame.name,
            }
            for frame in traceback.extract_tb(exc.__traceback__)
        ],
    }
    for attribute in ("status_code", "status"):
        status = getattr(exc, attribute, None)
        if isinstance(status, int) and 100 <= status <= 599:
            metadata["status_code"] = status
            break
    for attribute in ("code", "error_code"):
        code = getattr(exc, attribute, None)
        if isinstance(code, str) and SAFE_VALUE_PATTERN.fullmatch(code):
            metadata["error_code"] = code
            break
    return metadata


class JSONFormatter(logging.Formatter):
    """Format logs as JSON with safe request metadata."""

    def format(self, record) -> str:
        msg = super().format(record)

        log_data: dict[str, dict | str | None] = {"message": msg}

        # Extract request context if available
        if hasattr(record, "request") and isinstance(record.request, Request):
            try:
                log_data["method"] = record.request.method
                route = record.request.scope.get("route")
                log_data["route"] = getattr(route, "path", None)
                comparison_id = record.request.headers.get("x-comparison-id")
                if comparison_id:
                    log_data["comparison_id"] = str(uuid.UUID(comparison_id))

            except (AttributeError, TypeError, ValueError):
                pass
        # Include extra metadata if provided
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra

        return json.dumps(log_data)


def configure_logger() -> logging.Logger:
    """
    Configure and initialize application logger with multiple handlers.

    Sets up three logging destinations:
    1. Console (stdout) - human-readable format
    2. File (JSONL) - structured JSON for log analysis
    3. PostgreSQL - centralized database logging

    The logger uses different formatting for console vs file:
    - Console: Human-readable timestamp and function name
    - File: Structured JSON with request context

    Args:
        logger: Logger to configure

    Returns:
        Logger: Configured logger instance for "languia"

    Environment Variables:
        - LANGUIA_DEBUG: Set to "true" for DEBUG level, "false" for INFO
        - LOGDIR: Directory for log files (default "./data")
        - COMPARIA_DB_URI: PostgreSQL connection string for database logging
    """
    # TODO: log "funcName"
    logger = logging.getLogger("languia")

    # Log file naming with hostname and timestamp
    t = datetime.datetime.now()
    hostname = os.uname().nodename
    logger_filename = f"logs-{hostname}-{t.year}-{t.month:02d}-{t.day:02d}.jsonl"

    if settings.LANGUIA_DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    console_handler = RichHandler()
    # Use a more human-readable format for the console.
    console_formatter = logging.Formatter(
        "%(name)s - %(funcName)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    if settings.LOGDIR:
        os.makedirs(settings.LOGDIR, exist_ok=True)
        filename = os.path.join(settings.LOGDIR, logger_filename)
        file_handler = WatchedFileHandler(filename, encoding="utf-8")

        # Choisir le formatter en fonction de LOG_FORMAT
        if settings.LOG_FORMAT == "RAW":
            # Format identique à la console pour une meilleure lisibilité en dev
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            # Format JSON par défaut pour l'analyse automatisée
            file_formatter = JSONFormatter(
                '{"time":"%(asctime)s", "name": "%(name)s", \
                "level": "%(levelname)s", "message": "%(message)s"}',
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Custom Logger (Loki) handler for centralized logging
    custom_logger_url = os.getenv("CUSTOM_LOGGER_URL")
    if custom_logger_url:
        try:
            loki_handler = LokiHandler(
                url=f"{custom_logger_url}/loki/api/v1/push",
                tags={
                    "app": "comparia-backend",
                    "environment": os.getenv("ENVIR", "dev"),
                },
                version="1",
            )
            logger.addHandler(loki_handler)
        except Exception as e:
            print(f"Loki handler unavailable, skipping: {e}")

    return logger


def configure_uvicorn_logging() -> None:
    """
    Configure uvicorn/FastAPI loggers to use the same handlers as languia logger.

    Redirects uvicorn.access and uvicorn.error logs to the same backends:
    - File (JSON or RAW format based on LOG_FORMAT env var)
    - PostgreSQL (if configured)
    - Console (stdout)

    Call this after build_logger() to ensure uvicorn logs are captured.
    """
    log_format = os.getenv("LOG_FORMAT", "JSON").upper()

    # Configure uvicorn loggers
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = False

        if settings.LANGUIA_DEBUG:
            uvicorn_logger.setLevel(logging.DEBUG)
        else:
            uvicorn_logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_formatter)
        uvicorn_logger.addHandler(console_handler)

        # File handler
        if settings.LOGDIR:
            os.makedirs(settings.LOGDIR, exist_ok=True)
            t = datetime.datetime.now()
            hostname = os.uname().nodename
            uvicorn_log_filename = (
                f"uvicorn-{hostname}-{t.year}-{t.month:02d}-{t.day:02d}.jsonl"
            )
            filename = os.path.join(settings.LOGDIR, uvicorn_log_filename)
            file_handler = WatchedFileHandler(filename, encoding="utf-8")

            if settings.LOG_FORMAT == "RAW":
                file_formatter = logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            else:
                file_formatter = JSONFormatter(
                    '{"time":"%(asctime)s", "name": "%(name)s", \
                    "level": "%(levelname)s", "message": "%(message)s"}',
                    datefmt="%Y-%m-%d %H:%M:%S",
                )

            file_handler.setFormatter(file_formatter)
            uvicorn_logger.addHandler(file_handler)

        # Custom Logger (Loki) handler
        custom_logger_url = os.getenv("CUSTOM_LOGGER_URL")
        if custom_logger_url:
            try:
                loki_handler = LokiHandler(
                    url=f"{custom_logger_url}/loki/api/v1/push",
                    tags={
                        "app": "comparia-backend-uvicorn",
                        "environment": os.getenv("ENVIR", "dev"),
                    },
                    version="1",
                )
                uvicorn_logger.addHandler(loki_handler)
            except Exception as e:
                print(f"Loki handler unavailable for uvicorn, skipping: {e}")
