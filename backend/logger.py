import datetime
import json
import logging
import os
import sys
from logging.handlers import WatchedFileHandler

import psycopg2
from psycopg2 import sql


class JSONFormatter(logging.Formatter):
    """
    Custom logging formatter that outputs structured JSON.

    Converts log records to JSON with context information (IP, session, query params).
    Used for both file and database logging.
    """

    def format(self, record):
        """
        Format a log record as JSON with request context.

        Args:
            record: LogRecord from Python logging

        Returns:
            str: JSON-formatted log entry
        """
        msg = super().format(record)

        log_data = {"message": msg}

        # Extract request context if available
        if hasattr(record, "request"):
            try:
                log_data["query_params"] = dict(record.request.query_params)
                log_data["path_params"] = dict(record.request.path_params)
                # TODO: remove IP? (privacy concern)
                log_data["ip"] = get_ip(record.request)
                log_data["session_hash"] = record.request.session_hash

            except:
                pass
        # Include extra metadata if provided
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra

        return json.dumps(log_data)


class PostgresHandler(logging.Handler):
    """
    Custom logging handler that writes logs to PostgreSQL.

    Connects to database and stores log entries for centralized logging.
    Maintains persistent connection with auto-reconnection.
    """

    def __init__(self, dsn):
        """
        Initialize PostgreSQL logging handler.

        Args:
            dsn: Database connection string (postgres://user:pass@host/db)
        """
        super().__init__()
        self.dsn = dsn
        self.connection = None

    def connect(self):
        """Connect to PostgreSQL database, reconnecting if connection is closed."""
        if not self.connection or self.connection.closed:
            try:
                self.connection = psycopg2.connect(self.dsn)
            except psycopg2.Error as e:
                print(f"Error connecting to database: {e}")

    def emit(self, record):
        """
        Emit a log record by writing it to PostgreSQL.

        Args:
            record: LogRecord from Python logging
        """
        assert isinstance(record, logging.LogRecord)
        # print((record.__dict__))
        # print("LoggingHandler received LogRecord: {}".format(record))

        # record = super().format(record)
        self.format(record)

        try:
            self.connect()
            if self.connection:
                with self.connection.cursor() as cursor:
                    # del(record.__dict__["request"])

                    insert_statement = sql.SQL(
                        """
                        INSERT INTO logs (time, level, message, query_params, path_params, session_hash, extra)
                        VALUES (%(time)s, %(level)s, %(message)s, %(query_params)s, %(path_params)s, %(session_hash)s, %(extra)s)
                    """
                    )
                    values = {
                        "time": record.asctime,
                        "level": record.levelname,
                        "message": record.message,
                    }
                    if hasattr(record, "extra"):
                        values["extra"] = json.dumps(record.__dict__.get("extra"))
                    else:
                        values["extra"] = "{}"
                    if hasattr(record, "request"):
                        query_params = dict(record.request.query_params)
                        path_params = dict(record.request.path_params)
                        # ip = get_ip(record.request)
                        session_hash = record.request.session_hash
                        values["query_params"] = json.dumps(query_params)
                        values["path_params"] = json.dumps(path_params)
                        values["session_hash"] = str(session_hash)
                    else:
                        values["query_params"] = "{}"
                        values["path_params"] = "{}"
                        values["session_hash"] = ""

                    cursor.execute(insert_statement, values)
                    self.connection.commit()
        except psycopg2.Error as e:
            # Don't use logger on purpose to avoid endless loops
            print(f"Error logging to Postgres: {e}")
            # Could do:
            # self.handleError(record)


def build_logger(logger_filename):
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
        logger_filename: Filename for JSONL log output (relative to LOGDIR)

    Returns:
        Logger: Configured logger instance for "languia"

    Environment Variables:
        - LANGUIA_DEBUG: Set to "true" for DEBUG level, "false" for INFO
        - LOGDIR: Directory for log files (default "./data")
        - COMPARIA_DB_URI: PostgreSQL connection string for database logging
    """
    # TODO: log "funcName"
    logger = logging.getLogger("languia")
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    # Use a more human-readable format for the console.
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Récupérer le format de logs depuis la variable d'environnement
    log_format = os.getenv("LOG_FORMAT", "JSON").upper()

    if LOGDIR:
        os.makedirs(LOGDIR, exist_ok=True)
        filename = os.path.join(LOGDIR, logger_filename)
        file_handler = WatchedFileHandler(filename, encoding="utf-8")

        # Choisir le formatter en fonction de LOG_FORMAT
        if log_format == "RAW":
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

    if db and enable_postgres_handler:
        postgres_handler = PostgresHandler(db)
        logger.addHandler(postgres_handler)

    return logger


def configure_uvicorn_logging():
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

        if debug:
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
        if LOGDIR:
            os.makedirs(LOGDIR, exist_ok=True)
            t = datetime.datetime.now()
            hostname = os.uname().nodename
            uvicorn_log_filename = (
                f"uvicorn-{hostname}-{t.year}-{t.month:02d}-{t.day:02d}.jsonl"
            )
            filename = os.path.join(LOGDIR, uvicorn_log_filename)
            file_handler = WatchedFileHandler(filename, encoding="utf-8")

            if log_format == "RAW":
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

        # PostgreSQL handler
        if db and enable_postgres_handler:
            postgres_handler = PostgresHandler(db)
            uvicorn_logger.addHandler(postgres_handler)


# Log file naming with hostname and timestamp
t = datetime.datetime.now()
hostname = os.uname().nodename
log_filename = f"logs-{hostname}-{t.year}-{t.month:02d}-{t.day:02d}.jsonl"


logger = build_logger(log_filename)
configure_uvicorn_logging()

# Configurer le logger frontend pour utiliser les mêmes handlers
frontend_logger = logging.getLogger("frontend")
frontend_logger.setLevel(logging.DEBUG if debug else logging.INFO)
for handler in logger.handlers:
    frontend_logger.addHandler(handler)

# Log séparateur au démarrage pour marquer les redémarrages
logger.info("=" * 80)
