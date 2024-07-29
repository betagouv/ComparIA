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
if os.getenv('SENTRY_FRONT_DSN'):
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

if os.getenv("LANGUIA_CONTROLLER_URL"):
    controller_url = os.getenv("LANGUIA_CONTROLLER_URL")
else:
    controller_url = "http://localhost:21001"

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

models, all_models = get_model_list(
    controller_url,
    # TODO: directly pass api_endpoint_info instead
    register_api_endpoint_file,
    vision_arena=False,
)

api_endpoint_info = json.load(open(register_api_endpoint_file))

# TODO: to CSV

all_models_extra_info_json = {slugify(k.lower()): v for k, v in json.load(open("./models-extra-info.json")).items()}

models_extra_info = [build_model_extra_info(model, all_models_extra_info_json) for model in models]
print(models_extra_info)

headers = {"User-Agent": "FastChat Client"}
controller_url = None
enable_moderation = False
use_remote_storage = False
