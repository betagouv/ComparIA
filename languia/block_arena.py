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
from custom_components.customdropdown.backend.gradio_customdropdown import (
    CustomDropdown,
)
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
    # model_selectors = [None] * num_sides

    # TODO: check cookies on load!
    # tos_cookie = check_for_tos_cookie(request)
    welcome_modal = gr.HTML(welcome_modal_html, elem_id="welcome-modal-html")

    header = gr.HTML(header_html, elem_id="header-html")

    with gr.Column(
        elem_id="mode-screen",
        elem_classes="fr-mb-8w fr-container fr-grid-row fr-col-12 fr-col-lg-7 fr-col-md-8",
    ) as mode_screen:

        # TODO: rename component, it includes textbox
        model_dropdown = CustomDropdown(
            models=config.models_extra_info,
            # ignored, hardcoded in custom component
            choices=["random", "big-vs-small", "small-models", "reasoning", "custom"],
            # ignored, hardcoded in custom component
            interactive=True,
        )

        prompts_suggestions = gr.HTML(
            elem_classes="text-grey-200 fr-container fr-text--md fr-mt-md-5w fr-mt-5v fr-mb-0 fr-pb-0 fr-px-0",
            value="""<strong>Suggestions de prompts</strong>""",
        )
        guided_cards = CustomRadioCard(
            show_label=False,
            elem_id="guided-cards",
            elem_classes="fr-container fr-px-0",
            choices=config.guided_cards_choices,
            min_columns=1,
        )
        shuffle_link = gr.Button(
            scale=0,
            elem_classes="fr-icon-shuffle fr-btn--tertiary fr-mx-auto mobile-w-full",
            visible=False,
            value="Générer un autre message",
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
        
        with gr.Column(
            # h-screen
            visible=False,
            elem_classes="fr-container min-h-screen fr-pt-4w",
            elem_id="vote-area",
        ) as vote_area:
            gr.HTML(
                elem_classes="text-center",
                value="""
                <h4 class="fr-mt-2w fr-mb-1v">Quel modèle d’IA préférez-vous ?</h4>
                <p class="text-grey fr-text--sm">Avant de découvrir l’identité des modèles, nous avons besoin de votre préférence.<br />Elle permet d'enrichir les jeux de données compar:IA dont l’objectif est d’affiner les futurs modèles d’IA sur le français</p>""",
            )

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
                            ("Instructions non respectées", "instructions-not-followed"),
                        ],
                    )

                    comments_a = FrInput(
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

    with gr.Column(elem_id="send-area", elem_classes="fr-pt-1w", visible=False) as send_area:

        with gr.Row(
            elem_classes="flex-md-row flex-col items-start",
            visible=True,
        ) as send_row:
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

        results_area = gr.HTML(visible=True)

        footer_area = gr.HTML(visible=True, value=footer_html)

    # Modals
    #     with Modal(elem_id="retry-modal") as retry_modal:
    #         gr.HTML(
    #             """<h1 class="fr-modal__title"><span class="fr-icon-arrow-right-line fr-icon--lg"></span> Etes-vous sûr·e de quitter sans voter ?</h1>
    # <p>Vous êtes sur le point de recommencer une nouvelle conversation sans avoir voté sur celle-ci qui est en cours.</p>"""
    #         )
    #         with gr.Row():
    #             close_retry_modal_btn = gr.Button(
    #                 value="Non, annuler", elem_classes="fr-btn fr-btn--secondary", scale=1
    #             )
    #             retry_btn = gr.Button(
    #                 value="Oui, recommencer une conversation",
    #                 elem_classes="fr-btn",
    #                 scale=1,
    #             )

    from languia.listeners import register_listeners

    register_listeners()
