from languia.utils import get_model_list, get_matomo_js

import os
import argparse
import json

num_sides = 2
enable_moderation = False

parser = argparse.ArgumentParser()
parser.add_argument(
    "--controller-url",
    type=str,
    default="http://localhost:21001",
    help="The address of the controller",
)
# parser.add_argument(
#     "--concurrency-count",
#     type=int,
#     default=10,
#     help="The concurrency count of the gradio queue",
# )
# parser.add_argument(
#     "--model-list-mode",
#     type=str,
#     default="once",
#     choices=["once", "reload"],
#     help="Whether to load the model list once or reload the model list every time.",
# )
# parser.add_argument(
#     "--random-questions", type=str, help="Load random questions from a JSON file"
# )
parser.add_argument(
    "--register-api-endpoint-file",
    type=str,
    help="Register API-based model endpoints from a JSON file",
    default="register-api-endpoint-file.json",
)
# parser.add_argument(
#     "--elo-results-file", type=str, help="Load leaderboard results and plots"
# )
# parser.add_argument(
#     "--leaderboard-table-file", type=str, help="Load leaderboard results and plots"
# )
args, unknown = parser.parse_known_args()
# args = parser.parse_args()

controller_url = args.controller_url
enable_moderation = False
use_remote_storage = False
register_api_endpoint_file = args.register_api_endpoint_file

# load_js is before loading demo, head_js is on main component render, maybe group it or do head_js later?
# load_js = get_window_url_params_js

head_js = """
<script type="module" src="file=assets/dsfr/dsfr.module.js"></script>
<script type="text/javascript" nomodule src="file=assets/dsfr/dsfr.nomodule.js"></script>
"""
if os.getenv("MATOMO_ID") and os.getenv("MATOMO_URL"):
    head_js += get_matomo_js(os.getenv("MATOMO_URL"), os.getenv("MATOMO_ID"))


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


headers = {"User-Agent": "FastChat Client"}
controller_url = None
enable_moderation = False
use_remote_storage = False
