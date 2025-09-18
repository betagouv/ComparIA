"""
compar:IA's main code
Users chat with two anonymous models.
"""

import gradio as gr

# from gradio_modal import Modal

from languia.utils import (
    AppState,
)


from languia.custom_components.customchatbot import CustomChatbot
from languia.custom_components.customdropdown import CustomDropdown
from languia.custom_components.customradiocard import CustomRadioCard

from languia import config

with gr.Blocks(
    title="Discussion - compar:IA, le comparateur d'IA conversationnelles",
    analytics_enabled=False,
) as demo:

    app_state = gr.State(value=AppState())

    conv_a = gr.State()
    conv_b = gr.State()
    welcome_modal = gr.HTML("", elem_id="welcome-modal-html")
    header = gr.HTML("", elem_id="header-html")

    model_dropdown = CustomDropdown(
        models=config.models,
        # ignored, hardcoded in custom component
        choices=["random", "big-vs-small", "small-models", "reasoning", "custom"],
        # ignored, hardcoded in custom component
        interactive=True,
    )

    with gr.Group(
        elem_id="chat-area",
        visible=False,
        #  elem_classes="fr-pb-10w fr-pb-md-4w", visible=False
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
        reaction_json = gr.JSON(visible=False)

        with gr.Column(
            # h-screen
            visible=False,
            elem_classes="fr-container min-h-screen fr-pt-4w",
            elem_id="vote-area",
        ) as vote_area:

            which_model_radio = CustomRadioCard(
                min_columns=1,
                elem_id="vote-cards",
                choices=[
                    (
                        """Modèle A""",
                        "model-a",
                    ),
                    (
                        """Les deux se valent""",
                        "both-equal",
                    ),
                    (
                        """Modèle B""",
                        "model-b",
                    ),
                ],
                show_label=False,
            )

            with gr.Row(
                visible=False,
                elem_id="supervote-area",
                # FIXME: bottom margin too imprecise
                elem_classes="fr-grid-row fr-grid-row--gutters gap-0 fr-mt-8w fr-mb-md-16w fr-mb-16w",
            ) as supervote_area:

                with gr.Column(
                    elem_classes="fr-col-12 fr-col-md-6 fr-mr-md-n1w fr-mb-1w bg-white rounded-tile"
                ):

                    gr.HTML(
                        value="""<p><svg class="inline" width='26' height='26'><circle cx='13' cy='13' r='12' fill='#A96AFE' stroke='none'/></svg> <strong>Modèle A</strong></p>
        <p class="fr-mb-2w"><strong>Comment qualifiez-vous ses réponses ?</strong></p>"""
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
                            (
                                "Instructions non respectées",
                                "instructions-not-followed",
                            ),
                        ],
                    )

                    comments_a = gr.Textbox(
                        show_label=False,
                        visible=False,
                        lines=3,
                        placeholder="Les réponses du modèle A sont...",
                    )

                with gr.Column(
                    elem_classes="fr-col-12 fr-col-md-6 fr-ml-md-3w fr-mr-md-n3w fr-mb-1w bg-white rounded-tile"
                ):

                    gr.HTML(
                        value="""<p><svg class="inline" width='26' height='26'><circle cx='13' cy='13' r='12' fill='#ff9575' stroke='none'/></svg> <strong>Modèle B</strong></p>
        <p class="fr-mb-2w"><strong>Comment qualifiez-vous ses réponses ?</strong></p>"""
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
                            (
                                "Instructions non respectées",
                                "instructions-not-followed",
                            ),
                        ],
                    )
                    comments_b = gr.Textbox(
                        show_label=False,
                        visible=False,
                        lines=3,
                        placeholder="Les réponses du modèle B sont...",
                    )
                comments_link = gr.Button(
                    elem_classes="link fr-mt-1w", value="Ajouter des détails"
                )

    with gr.Column(
        elem_id="send-area", elem_classes="fr-pt-1w", visible=False
    ) as send_area:

        with gr.Row(
            elem_classes="flex-md-row flex-col items-start",
            visible=True,
        ) as send_row:
            textbox = gr.Textbox(
                elem_id="main-textbox",
                show_label=False,
                lines=1,
                placeholder="Continuer à discuter avec les deux modèles d'IA",
                max_lines=7,
                elem_classes="w-full",
                container=True,
                autofocus=True,
            )
            send_btn = gr.Button(
                interactive=False,
                # scale=1,
                value="Envoyer",
                # icon="assets/dsfr/icons/system/arrow-up-line.svg",
                elem_id="send-btn",
                elem_classes="grow-0 purple-btn w-full fr-ml-md-1w",
            )

        with gr.Row(elem_classes="fr-grid-row fr-grid-row--center"):
            conclude_btn = gr.Button(
                size="lg",
                value="Passer à la révélation des modèles",
                elem_classes="fr-col-12 fr-col-md-5 purple-btn fr-mt-1w",
                visible=False,
                interactive=False,
            )

    with gr.Column(
        elem_classes="fr-container--fluid fr-py-2w fr-grid-row",
        elem_id="buttons-footer",
        visible=False,
    ) as buttons_footer:

        supervote_send_btn = gr.Button(
            elem_classes="purple-btn fr-mx-auto fr-col-10 fr-col-md-4",
            value="Passer à la révélation des modèles",
            size="lg",
            interactive=False,
        )

    with gr.Column(
        elem_id="reveal-screen", visible=False, elem_classes="min-h-screen fr-pt-4w"
    ) as reveal_screen:

        results_area = gr.HTML()

        footer_area = gr.HTML()


    available_models = gr.JSON(visible=False)
    reveal_data = gr.JSON(visible=False)

    from languia.listeners import register_listeners

    register_listeners()
