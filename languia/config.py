from languia.utils import get_model_list, get_matomo_js, build_model_extra_info

import os
import sentry_sdk
import json
import logging
from slugify import slugify

num_sides = 2
enable_moderation = False

if os.getenv("GIT_COMMIT"):
    git_commit = os.getenv("GIT_COMMIT")

env_debug = os.getenv("LANGUIA_DEBUG")

if env_debug:
    if env_debug.lower() == "true":
        debug = True
    else:
        debug = False
else:
    debug = False

if not debug:
    assets_absolute_path = "/app/assets"
else:
    assets_absolute_path = os.path.dirname(__file__) + "/assets"

if os.getenv("SENTRY_SAMPLE_RATE"):
    traces_sample_rate = float(os.getenv("SENTRY_SAMPLE_RATE"))
else:
    traces_sample_rate = 0.2

if os.getenv("SENTRY_DSN"):
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    # We recommend adjusting this value in production.
    if os.getenv("SENTRY_ENV"):
        sentry_env = os.getenv("SENTRY_ENV")
    else:
        sentry_env = "development"
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        environment=sentry_env,
        traces_sample_rate=traces_sample_rate,
    )
    logging.info("Sentry loaded with traces_sample_rate=" + str(traces_sample_rate))

# TODO: https://docs.sentry.io/platforms/javascript/install/loader/#custom-configuration
if os.getenv("SENTRY_FRONT_DSN"):
    sentry_js = f"""
    <script src="{ os.getenv('SENTRY_FRONT_DSN') }" crossorigin="anonymous"></script>
    """
    # sentry_js += """
    # <script>
    # Sentry.onLoad(function() {
    #     Sentry.init({
    #     // Performance Monitoring
    # """
    # sentry_js += f"""
    #   tracesSampleRate: {traces_sample_rate},
    #   // Session Replay
    #   replaysSessionSampleRate: 0.1, // This sets the sample rate at 10%. You may want to change it to 100% while in development and then sample at a lower rate in production.
    #   replaysOnErrorSampleRate: 1.0, // If you're not already sampling the entire session, change the sample rate to 100% when sampling sessions where errors occur.
    #   """
    # sentry_js += """
    #     });
    # });
    # </script>"""
else:
    sentry_js = ""

# if os.getenv("LANGUIA_CONTROLLER_URL"):
#     controller_url = os.getenv("LANGUIA_CONTROLLER_URL")
# else:
#     controller_url = "http://localhost:21001"

if os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE"):
    register_api_endpoint_file = os.getenv("LANGUIA_REGISTER_API_ENDPOINT_FILE")
else:
    register_api_endpoint_file = "register-api-endpoint-file.json"

enable_moderation = False
use_remote_storage = False

if os.getenv("MATOMO_ID") and os.getenv("MATOMO_URL"):
    matomo_js = get_matomo_js(os.getenv("MATOMO_URL"), os.getenv("MATOMO_ID"))
else:
    matomo_js = ""

# we can also load js normally (no in <head>)
arena_head_js = (
    sentry_js
    + """
<script type="module" src="file=assets/dsfr/dsfr.module.js"></script>
<script type="text/javascript" nomodule src="file=assets/dsfr/dsfr.nomodule.js"></script>
"""
    + matomo_js
)

site_head_js = (
    # sentry_js
    # +
    """
<script type="module" src="assets/dsfr/dsfr.module.js"></script>
<script type="text/javascript" nomodule src="assets/dsfr/dsfr.nomodule.js"></script>
"""
    + matomo_js
)

with open("./assets/dsfr-arena.css", encoding="utf-8") as css_file:
    css_dsfr = css_file.read()
with open("./assets/custom-arena.css", encoding="utf-8") as css_file:
    custom_css = css_file.read()

css = css_dsfr + custom_css

models = get_model_list(
    None,
    # TODO: directly pass api_endpoint_info instead
    register_api_endpoint_file,
)

api_endpoint_info = json.load(open(register_api_endpoint_file))

# TODO: to CSV

all_models_extra_info_json = {
    slugify(k.lower()): v
    for k, v in json.load(open("./models-extra-info.json")).items()
}

models_extra_info = [
    build_model_extra_info(model, all_models_extra_info_json) for model in models
]
print(models_extra_info)

headers = {"User-Agent": "FastChat Client"}
controller_url = None
enable_moderation = False
use_remote_storage = False

BLIND_MODE_INPUT_CHAR_LEN_LIMIT = int(
    os.getenv("FASTCHAT_BLIND_MODE_INPUT_CHAR_LEN_LIMIT", 24000)
)

SAMPLING_WEIGHTS = {
    # tier 0
    "gpt-4-0314": 4,
    "gpt-4-0613": 4,
    "gpt-4-1106-preview": 2,
    "gpt-4-0125-preview": 4,
    "gpt-4-turbo-2024-04-09": 4,
    "gpt-3.5-turbo-0125": 2,
    "claude-3-opus-20240229": 4,
    "claude-3-sonnet-20240229": 4,
    "claude-3-haiku-20240307": 4,
    "claude-2.1": 1,
    "zephyr-orpo-141b-A35b-v0.1": 2,
    "dbrx-instruct": 1,
    "command-r-plus": 4,
    "command-r": 2,
    "reka-flash": 4,
    "reka-flash-online": 4,
    "qwen1.5-72b-chat": 2,
    "qwen1.5-32b-chat": 2,
    "qwen1.5-14b-chat": 2,
    "qwen1.5-7b-chat": 2,
    "gemma-1.1-7b-it": 2,
    "gemma-1.1-2b-it": 1,
    "mixtral-8x7b-instruct-v0.1": 4,
    "mistral-7b-instruct-v0.2": 2,
    "mistral-large-2402": 4,
    "mistral-medium": 2,
    "starling-lm-7b-beta": 2,
    # tier 1
    "deluxe-chat-v1.3": 2,
    "llama-2-70b-chat": 2,
    "llama-2-13b-chat": 1,
    "llama-2-7b-chat": 1,
    "vicuna-33b": 1,
    "vicuna-13b": 1,
    "yi-34b-chat": 1,
}
# target model sampling weights will be boosted.
BATTLE_TARGETS = {
    "gpt-4-turbo-2024-04-09": {
        "gpt-4-1106-preview",
        "gpt-4-0125-preview",
        "claude-3-opus-20240229",
        "gemini-pro-dev-api",
    },
    "gemini-pro-dev-api": {
        "gpt-4-turbo-2024-04-09",
        "claude-3-opus-20240229",
        "gpt-4-0125-preview",
        "claude-3-sonnet-20240229",
    },
    "reka-flash": {
        "qwen1.5-72b-chat",
        "claude-3-haiku-20240307",
        "command-r-plus",
        "command-r",
    },
    "reka-flash-online": {
        "qwen1.5-72b-chat",
        "claude-3-haiku-20240307",
        "command-r-plus",
        "command-r",
    },
    "deluxe-chat-v1.3": {
        "gpt-4-1106-preview",
        "gpt-4-0125-preview",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
    },
    "qwen1.5-32b-chat": {
        "gpt-3.5-turbo-0125",
        "gpt-4-0613",
        "gpt-4-0125-preview",
        "llama-2-70b-chat",
        "mixtral-8x7b-instruct-v0.1",
        "mistral-large-2402",
        "yi-34b-chat",
    },
    "qwen1.5-14b-chat": {
        "starling-lm-7b-alpha",
        "claude-3-haiku-20240307",
        "gpt-3.5-turbo-0125",
        "openchat-3.5-0106",
        "mixtral-8x7b-instruct-v0.1",
    },
    "mistral-large-2402": {
        "gpt-4-0125-preview",
        "gpt-4-0613",
        "mixtral-8x7b-instruct-v0.1",
        "mistral-medium",
        "mistral-next",
        "claude-3-sonnet-20240229",
    },
    "gemma-1.1-2b-it": {
        "gpt-3.5-turbo-0125",
        "mixtral-8x7b-instruct-v0.1",
        "starling-lm-7b-beta",
        "llama-2-7b-chat",
        "mistral-7b-instruct-v0.2",
        "gemma-1.1-7b-it",
    },
    "zephyr-orpo-141b-A35b-v0.1": {
        "qwen1.5-72b-chat",
        "mistral-large-2402",
        "command-r-plus",
        "claude-3-haiku-20240307",
    },
}

SAMPLING_BOOST_MODELS = []

# outage models won't be sampled.
OUTAGE_MODELS = []
