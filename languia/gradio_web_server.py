import argparse

from themes.dsfr import DSFR

import gradio as gr

from languia.block_arena import (
    build_arena,
    load_demo_arena,
    set_global_vars_anony,
)

from languia.block_conversation import (
    set_global_vars,
    # build_about,
    get_model_list,
    get_ip,
)
# from fastchat.serve.monitor.monitor import build_leaderboard_tab
from fastchat.utils import build_logger
from languia.utils import get_matomo_js, header_html

import os

logger = build_logger("gradio_web_server", "gradio_web_server.log")


def load_demo(request: gr.Request):
    global models, all_models

    ip = get_ip(request)
    logger.info(f"load_demo. ip: {ip}")

    # selected = 0
    # if "arena" in url_params:
    #     selected = 0
    # elif "leaderboard" in url_params:
    #     selected = 4
    # elif "about" in url_params:
    #     selected = 5

    # if args.model_list_mode == "reload":
    #     models, all_models = get_model_list(
    #         args.controller_url,
    #         args.register_api_endpoint_file,
    #         vision_arena=False,
    #     )

    arena_updates = load_demo_arena(all_models)

    # return (gr.Tabs(selected=selected),) + arena_updates
    return (gr.Blocks(),) + arena_updates


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


# Set global variables
set_global_vars(args.controller_url, enable_moderation_=False, use_remote_storage_=False)
models, all_models = get_model_list(
    args.controller_url,
    args.register_api_endpoint_file,
    vision_arena=False,
)

# load_js is before loading demo, head_js is on main component render, maybe group it or do head_js later?
# load_js = get_window_url_params_js

head_js = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script type="module" src="file=assets/js/dsfr.module.js"></script>
<script type="text/javascript" nomodule src="file=assets/js/dsfr.nomodule.js"></script>
"""
if os.getenv("MATOMO_ID") and os.getenv("MATOMO_URL"):
    head_js += get_matomo_js(os.getenv("MATOMO_URL"), os.getenv("MATOMO_ID"))


with open("./assets/dsfr.css", encoding="utf-8") as css_file:
    css_dsfr = css_file.read()
with open("./assets/custom.css", encoding="utf-8") as css_file:
    custom_css = css_file.read()

css = css_dsfr + custom_css

with gr.Blocks(
    title="LANGU:IA – L'arène francophone de comparaison de modèles conversationnels",
    theme=DSFR(),
    css=css,
    head=head_js,
    # elem_classes=""
) as demo:
    # TODO: skiplinks
    if os.getenv("GIT_COMMIT"):
        git_commit = os.getenv("GIT_COMMIT")
        header_html += f"<!-- Git commit: {git_commit} -->"

    gr.HTML(header_html, elem_id="header_html")

    with gr.Blocks(
        elem_id="main-component",
        elem_classes="fr-container",
        # TODO: to test
        #  fill_height=True
        # Delete cache every second
        # delete_cache=(1,1),
    ) as pages:

        with gr.Column(elem_id="arena", elem_classes="") as arena:
            # with gr.Blocks(elem_id="arena", elem_classes="fr-grid-row") as arena:
            two_models_arena = build_arena(models)

    demo.load(
        load_demo,
        # [url_params],
        # js=load_js,
    )
