from languia.utils import get_model_list, get_matomo_js, get_model_extra_info

import os
import argparse
import json

num_sides = 2
enable_moderation = False


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
    """
<script type="module" src="file=assets/dsfr/dsfr.module.js"></script>
<script type="text/javascript" nomodule src="file=assets/dsfr/dsfr.nomodule.js"></script>
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

all_models_extra_info = {k.lower(): v for k, v in json.load(open("./models-extra-info.json")).items()}

headers = {"User-Agent": "FastChat Client"}
controller_url = None
enable_moderation = False
use_remote_storage = False
