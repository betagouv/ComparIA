"""
compar:IA's main code
Users chat with two anonymous models.
"""

from languia.themes.dsfr import DSFR

import gradio as gr

# from gradio_modal import Modal

from languia.utils import (
    header_html,
    welcome_modal_html,
    footer_html,
    AppState,
    second_header_html,
)


from custom_components.customchatbot.backend.gradio_customchatbot import CustomChatbot


from languia import config

with gr.Blocks(
    title="Discussion - compar:IA, le comparateur d'IA conversationnelles",
    theme=DSFR(),
    css=config.css,
    head=config.arena_head_js,
    analytics_enabled=False,
    # scroll_to_output = True,
    js=config.arena_js,
    # Doesn't work with uvicorn
    # delete_cache=(1, 1) if config.debug else None,
) as demo:

    app_state = gr.State(value=AppState())

    conv_a = gr.State()
    conv_b = gr.State()
    welcome_modal = gr.HTML(welcome_modal_html, elem_id="welcome-modal-html")

    header = gr.HTML(header_html, elem_id="header-html")

    with gr.Group(
        elem_id="chat-area", elem_classes="fr-pb-10w fr-pb-md-0", visible=False
    ) as chat_area:

        chatbot = CustomChatbot(
            elem_id="main-chatbot",
            height="100%",
            placeholder="<em>Veuillez écrire aux modèles</em>",
            layout="panel",  # no effect
            likeable=True,
            # UserWarning: show_label has no effect when container is False.
            show_label=False,
            container=False,
            elem_classes="chatbot",
            show_copy_button=True,
            # autoscroll=True
        )


    from languia.listeners import register_listeners

    register_listeners()
