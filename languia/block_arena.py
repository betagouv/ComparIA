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
)


from custom_components.customchatbot.backend.gradio_customchatbot import CustomChatbot

from custom_components.customradiocard.backend.gradio_customradiocard import (
    CustomRadioCard,
)

from custom_components.frinput.backend.gradio_frinput import FrInput

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
    which_model_radio = CustomRadioCard(
            min_columns=1,
            elem_id="vote-cards",
            elem_classes="justify-center fr-mx-auto fr-col-12 fr-col-md-8",
            choices=[
                (
                    """<div class="self-center justify-center"><svg class="inline" width='26' height='26'><circle cx='13' cy='13' r='12' fill='#A96AFE' stroke='none'/></svg> <span class="">Modèle A</span>
                </div>""",
                    "model-a",
                ),
                (
                    """<span class="self-center text-center justify-center">Les deux se valent</span>""",
                    "both-equal",
                ),
                (
                    """<div class="self-center"><svg class="inline" width='26' height='26'><circle cx='13' cy='13' r='12' fill='#ff9575' stroke='none'/></svg><span class=""> Modèle B</span>
                </div>""",
                    "model-b",
                ),
            ],
            show_label=False,
        )

    positive_a = gr.CheckboxGroup(
            elem_classes="thumb-up-icon flex-important checkboxes fr-mb-2w",
            show_label=False,
            choices=[
                ("Utiles", "useful"),
                ("Complètes", "complete"),
                ("Créatives", "creative"),
                ("Mise en forme claire", "clear-formatting"),
            ],
        )

    negative_a = gr.CheckboxGroup(
            elem_classes="thumb-down-icon flex-important checkboxes fr-mb-2w",
            show_label=False,
            choices=[
                ("Incorrectes", "incorrect"),
                ("Superficielles", "superficial"),
                ("Instructions non respectées", "instructions-not-followed"),
            ],
        )

    comments_a = FrInput(
            show_label=False,
            visible=False,
            lines=3,
            placeholder="Les réponses du modèle A sont...",
        )


    positive_b = gr.CheckboxGroup(
            elem_classes="thumb-up-icon flex-important checkboxes fr-mb-2w",
            show_label=False,
            choices=[
                ("Utiles", "useful"),
                ("Complètes", "complete"),
                ("Créatives", "creative"),
                ("Mise en forme claire", "clear-formatting"),
            ],
        )

    negative_b = gr.CheckboxGroup(
            elem_classes="thumb-down-icon flex-important checkboxes fr-mb-2w",
            show_label=False,
            choices=[
                ("Incorrectes", "incorrect"),
                ("Superficielles", "superficial"),
                ("Instructions non respectées", "instructions-not-followed"),
            ],
        )
    comments_b = FrInput(
            show_label=False,
            visible=False,
            lines=3,
            placeholder="Les réponses du modèle B sont...",
        )
    comments_link = gr.Button(
        elem_classes="link fr-mt-1w", value="Ajouter des détails"
    )

    textbox = FrInput(
            elem_id="main-textbox",
            show_label=False,
            lines=1,
            placeholder="Continuer à discuter avec les deux modèles d'IA",
            max_lines=7,
            elem_classes="w-full",
            container=True,
            autofocus=True,
        )
    vote_btn = gr.Button(
            size="lg",
            value="Passer à la révélation des modèles",
            elem_classes="fr-col-12 fr-col-md-5 purple-btn fr-mt-1w",
            visible=False,
            interactive=False,
        )


    from languia.listeners import register_listeners

    register_listeners()
