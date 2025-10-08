import os
import sentry_sdk
import json5
import sys
import datetime
from pathlib import Path
import logging
from logging.handlers import WatchedFileHandler
from languia.logs import JSONFormatter, PostgresHandler
from httpx import Timeout

GLOBAL_TIMEOUT = Timeout(10.0, read=10.0, write=5.0, connect=10.0)

OBJECTIVE = 200_000

MAX_INPUT_CHARS_PER_HOUR = 200_000

SMALL_MODELS_BUCKET_UPPER_LIMIT = 60
BIG_MODELS_BUCKET_LOWER_LIMIT = 100

env_debug = os.getenv("LANGUIA_DEBUG")

RATELIMIT_PRICEY_MODELS_INPUT = 50_000

if env_debug:
    if env_debug.lower() == "true":
        debug = True
    else:
        debug = False
else:
    debug = False

t = datetime.datetime.now()
hostname = os.uname().nodename
log_filename = f"logs-{hostname}-{t.year}-{t.month:02d}-{t.day:02d}.jsonl"

LOGDIR = os.getenv("LOGDIR", "./data")

db = os.getenv("COMPARIA_DB_URI", None)
enable_postgres_handler = True


def build_logger(logger_filename):
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

    file_formatter = JSONFormatter(
        '{"time":"%(asctime)s", "name": "%(name)s", \
        "level": "%(levelname)s", "message": "%(message)s"}',
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if LOGDIR:
        os.makedirs(LOGDIR, exist_ok=True)
        filename = os.path.join(LOGDIR, logger_filename)
        file_handler = WatchedFileHandler(filename, encoding="utf-8")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    if db and enable_postgres_handler:
        postgres_handler = PostgresHandler(db)
        logger.addHandler(postgres_handler)

    return logger


logger = build_logger(log_filename)

if os.getenv("GIT_COMMIT"):
    git_commit = os.getenv("GIT_COMMIT")
else:
    git_commit = None

if not debug:
    assets_absolute_path = "/app/assets"
else:
    assets_absolute_path = os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    )
    # print("assets_absolute_path: "+assets_absolute_path)
if os.getenv("SENTRY_SAMPLE_RATE"):
    traces_sample_rate = float(os.getenv("SENTRY_SAMPLE_RATE"))
else:
    traces_sample_rate = 0.2

profiles_sample_rate = traces_sample_rate

if os.getenv("SENTRY_DSN"):
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    if os.getenv("SENTRY_ENV"):
        sentry_env = os.getenv("SENTRY_ENV")
    else:
        sentry_env = "development"
    sentry_sdk.init(
        release=git_commit,
        attach_stacktrace=True,
        dsn=os.getenv("SENTRY_DSN"),
        environment=sentry_env,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        project_root=os.getcwd(),
    )
    logger.debug(
        "Sentry loaded with traces_sample_rate="
        + str(traces_sample_rate)
        + " and profiles_sample_rate="
        + str(profiles_sample_rate)
        + " for release "
        + str(git_commit)
    )


all_models = json5.loads(Path("./utils/models/generated-models.json").read_text())

from languia.utils import filter_enabled_models

models = filter_enabled_models(all_models)

reasoning_models = [id for id, model in models.items() if model.get("reasoning", False)]

random_pool = [id for id, _model in models.items() if id not in reasoning_models]

small_models = [
    id
    for id, model in models.items()
    if model["params"] <= 60
    and id not in reasoning_models
]

big_models = [
    id
    for id, model in models.items()
    if model["params"] >= 100
    and id not in reasoning_models
]

pricey_models = [id for id, model in models.items() if model.get("pricey", False)]

headers = {"User-Agent": "FastChat Client"}

if os.getenv("LANGUIA_CONTROLLER_URL") is not None:
    controller_url = os.getenv("LANGUIA_CONTROLLER_URL")
else:
    controller_url = "http://localhost:21001"


def get_model_system_prompt(model_name):
    if "chocolatine" in model_name or "lfm-40b" in model_name:
        return "Tu es un assistant IA serviable et bienveillant. Tu fais des réponses concises et précises."
    else:
        return None
