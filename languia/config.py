import os
import sentry_sdk
import json5
import sys
from languia.utils import get_model_names_list, get_matomo_js, build_model_extra_info
import datetime
from pathlib import Path

env_debug = os.getenv("LANGUIA_DEBUG")

MAX_INPUT_CHARS_PER_HOUR = 200_000

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
import logging

LOGDIR = os.getenv("LOGDIR", "./data")

from logging.handlers import WatchedFileHandler

from languia.logs import JSONFormatter, PostgresHandler

from httpx import Timeout

GLOBAL_TIMEOUT = Timeout(10.0, read=10.0, write=5.0, connect=10.0)

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
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
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

num_sides = 2
enable_moderation = False

objective = 150_000

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


# TODO: https://docs.sentry.io/platforms/javascript/install/loader/#custom-configuration
if os.getenv("SENTRY_FRONT_DSN"):
    sentry_head_js = f"""
 <script type="text/javascript" 
   src="../assets/bundle.tracing.replay.min.js"
 ></script>"""
else:
    sentry_head_js = ""


if os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE"):
    register_api_endpoint_file = os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE")
else:
    register_api_endpoint_file = "register-api-endpoint-file.json"

enable_moderation = False
use_remote_storage = False

# TODO: https://docs.sentry.io/platforms/javascript/install/loader/#custom-configuration
if os.getenv("SENTRY_FRONT_DSN"):
    sentry_head_js = f"""
 <script type="text/javascript" 
   src="../assets/bundle.tracing.replay.min.js"
 ></script>"""
else:
    sentry_head_js = ""

if os.getenv("MATOMO_ID") and os.getenv("MATOMO_URL"):
    matomo_js = get_matomo_js(os.getenv("MATOMO_URL"), os.getenv("MATOMO_ID"))
else:
    matomo_js = ""

# we can also load js normally (no in <head>)
arena_head_js = (
    sentry_head_js
    + """
<script type="module" src="../assets/dsfr/dsfr.module.js"></script>
<script type="text/javascript" nomodule src="../assets/dsfr/dsfr.nomodule.js"></script>
<script type="text/javascript">
function createSnackbar(message) {
    const snackbar = document.getElementById('snackbar');
    const messageText = snackbar.querySelector('.message');
    messageText.textContent = message;

    snackbar.classList.add('show');

    setTimeout(() => {
        snackbar.classList.remove('show');
    }, 2000);
}
function closeSnackbar() {
    const snackbar = document.getElementById('snackbar');
    snackbar.classList.remove('show');
}

function copie() {
    const copyText = document.getElementById("share-link");
    copyText.select();
    copyText.setSelectionRange(0, 99999);
    navigator.clipboard.writeText(copyText.value);
    createSnackbar("Lien copié dans le presse-papiers");
}
</script>
"""
    + matomo_js
)

site_head_js = (
    """
<script type="module" src="assets/dsfr/dsfr.module.js"></script>
<script type="text/javascript" nomodule src="assets/dsfr/dsfr.nomodule.js"></script>
"""
    + matomo_js
)

with open("./assets/arena.js", encoding="utf-8") as js_file:
    arena_js = js_file.read()

    if os.getenv("GIT_COMMIT"):
        git_commit = os.getenv("GIT_COMMIT")
        arena_js = arena_js.replace("__GIT_COMMIT__", os.getenv("GIT_COMMIT"))

    if os.getenv("SENTRY_FRONT_DSN"):
        arena_js = arena_js.replace(
            "__SENTRY_FRONT_DSN__", os.getenv("SENTRY_FRONT_DSN")
        )
    if os.getenv("SENTRY_ENV"):
        arena_js = arena_js.replace("__SENTRY_ENV__", os.getenv("SENTRY_ENV"))

with open("./assets/dsfr-arena.css", encoding="utf-8") as css_file:
    css_dsfr = css_file.read()
with open("./assets/custom-arena.css", encoding="utf-8") as css_file:
    custom_css = css_file.read()
with open("./assets/dark.css", encoding="utf-8") as css_file:
    darkfixes_css = css_file.read()

# css = custom_css + darkfixes_css
css = css_dsfr + custom_css + darkfixes_css


api_endpoint_info = json5.load(open(register_api_endpoint_file))

models = get_model_names_list(api_endpoint_info)

all_models_extra_info_toml = json5.loads(
    Path("./utils/models/generated-models.json").read_text()
)
# TODO: refacto?
models_extra_info = [
    all_models_extra_info_toml[model]
    for model in models
    if model is not None and all_models_extra_info_toml.get(model)
]

models_extra_info.sort(key=lambda x: x["simple_name"])

headers = {"User-Agent": "FastChat Client"}

if os.getenv("LANGUIA_CONTROLLER_URL") is not None:
    controller_url = os.getenv("LANGUIA_CONTROLLER_URL")
else:
    controller_url = "http://localhost:21001"

enable_moderation = False
use_remote_storage = False


def get_model_system_prompt(model_name):
    if "chocolatine" in model_name or "lfm-40b" in model_name:
        return "Tu es un assistant IA serviable et bienveillant. Tu fais des réponses concises et précises."
    else:
        return None


BLIND_MODE_INPUT_CHAR_LEN_LIMIT = 60_000


# unavailable models won't be sampled.
unavailable_models = []

