import argparse

from themes.dsfr import DSFR

import gradio as gr

from languia.block_arena import (
    build_arena,
    load_demo_arena,
)

from languia import config

# from fastchat.serve.monitor.monitor import build_leaderboard_tab
from fastchat.utils import build_logger
from languia.utils import get_ip

import os

logger = build_logger("gradio_web_server", "gradio_web_server.log")


def load_demo(request: gr.Request):
    ip = get_ip(request)
    logger.info(f"load_demo. ip: {ip}")

    arena_updates = load_demo_arena(config.all_models)

    # return (gr.Tabs(selected=selected),) + arena_updates
    return (gr.Blocks(),) + arena_updates

with gr.Blocks(
    title="LANGU:IA – L'arène francophone de comparaison de modèles conversationnels",
    theme=DSFR(),
    css=config.css,
    head=config.head_js,
    # elem_classes=""
) as demo:
    # TODO: skiplinks

    with gr.Blocks(
        # elem_id="main-component",
        elem_id="arena",
        # elem_classes="fr-container",
        # TODO: to test
        #  fill_height=True
        # Delete cache every second
        # delete_cache=(1,1),
    ) as pages:

        # with gr.Column(elem_id="arena", elem_classes="") as arena:
            # with gr.Blocks(elem_id="arena", elem_classes="fr-grid-row") as arena:
        two_models_arena = build_arena(config.models)

    demo.load(
        load_demo,
        # [url_params],
        # js=load_js,   
    )
