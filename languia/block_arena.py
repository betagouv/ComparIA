"""
LANGU:IA's main code
Users chat with two anonymous models.
"""

from themes.dsfr import DSFR

import gradio as gr

# from gradio_modal import Modal

from languia.utils import header_html, welcome_modal_html

# from custom_components.frbutton.backend.gradio_frbutton import FrButton
from custom_components.customradiocard.backend.gradio_customradiocard import (
    CustomRadioCard,
)

from custom_components.frinput.backend.gradio_frinput import FrInput

from languia import config

# // Enable navigation prompt
# window.onbeforeunload = function() {
#     return true;
# };
# // Remove navigation prompt
# window.onbeforeunload = null;

app_state = gr.State()


with gr.Blocks(
    title="LANGU:IA – Le comparateur d'IA conversationnelles",
    theme=DSFR(),
    css=config.css,
    head=config.arena_head_js,
    analytics_enabled=False,
    # scroll_to_output = True,
    js=config.arena_js,
    # Doesn't work with uvicorn
    # delete_cache=(1, 1) if config.debug else None,
) as demo:

    conv_a = gr.State()
    conv_b = gr.State()
    conversations = [conv_a, conv_b]
    # model_selectors = [None] * num_sides

    # TODO: check cookies on load!
    # tos_cookie = check_for_tos_cookie(request)
    # if not tos_cookie:
    welcome_modal = gr.HTML(welcome_modal_html, elem_id="welcome-modal-html")

    # gr.HTML(elem_id="header-placeholder")
    header = gr.HTML(header_html, elem_id="header-html")

    with gr.Column(elem_id="mode-screen", elem_classes="fr-mb-8w") as mode_screen:

        title = gr.HTML(
            # Sur Figma: fr-mt-8w
            elem_classes="text-center text-grey-200 fr-mt-4w fr-mb-2w",
            value="""<h3>Comment puis-je vous aider aujourd'hui ?</h3>""",
        )

        guided_cards = CustomRadioCard(
            show_label=False,
            elem_classes="fr-col-12 fr-col-md-8 fr-mx-auto",
            choices=[
                (
                    """<div><img class="fr-mb-3w" src="file=assets/extra-icons/lightbulb.svg" /><p>Générer de nouvelles idées</p></div>""",
                    "vie-professionnelle",
                ),
                (
                    """<div><img class="fr-mb-3w" src="file=assets/extra-icons/chat-3.svg" /><p>Expliquer simplement un concept</p>""",
                    "expression",
                ),
                (
                    """<div><img class="fr-mb-3w" src="file=assets/extra-icons/translate-2.svg" /><p>M’exprimer dans une autre langue</p></div>""",
                    "langues",
                ),
                (
                    """<div><img class="fr-mb-3w" src="file=assets/extra-icons/draft.svg" /><p>Rédiger un document administratif</p></div>""",
                    "administratif",
                ),
                (
                    """<div><img class="fr-mb-3w" src="file=assets/extra-icons/bowl.svg" /><p>Découvrir une nouvelle recette de cuisine</p></div>""",
                    "loisirs",
                ),
                (
                    """<div><img class="fr-mb-3w" src="file=assets/extra-icons/clipboard.svg" /><p>Créer un programme d’entraînement</p></div>""",
                    "conseils",
                ),
                (
                    """<div><img class="fr-mb-3w" src="file=assets/extra-icons/earth.svg" /><p>Organiser mon prochain voyage</p></div>""",
                    "loisirs",
                ),
                (
                    """<div><img class="fr-mb-3w" src="file=assets/extra-icons/music-2.svg" /><p>Proposer des idées de films, livres, musiques</p></div>""",
                    "loisirs",
                ),
            ],
        )
        shuffle_link = gr.Button(
            scale=1,
            elem_classes="fr-mx-auto link",
            visible=False,
            value="Me proposer un autre prompt",
            # icon="assets/extra-icons/shuffle.svg",
        )

    with gr.Group(
        elem_id="chat-area", elem_classes="fr-mb-10w fr-mb-md-0", visible=False
    ) as chat_area:

        # {likeable}
        # placeholder
        #         placeholder
        # a placeholder message to display in the chatbot when it is empty. Centered vertically and horizontally in the Chatbot. Supports Markdown and HTML.
        chatbot = gr.Chatbot(
            # TODO:
            type="messages",
            elem_id="main-chatbot",
            # min_width=
            # height="100vh",
            # height="max(100vh, 100%)",
            height="100%",
            # Doesn't show because it always has at least our message
            # Note: supports HTML, use it!
            placeholder="<em>Veuillez écrire aux modèles</em>",
            # No difference
            # bubble_full_width=False,
            layout="panel",  # or "bubble"
            likeable=False,
            # UserWarning: show_label has no effect when container is False.
            show_label=False,
            container=False,
            elem_classes="chatbot",
            # Should we show it?
            show_copy_button=False,
            # autoscroll=True
        )

    with gr.Column(
        elem_id="send-area", visible=True, elem_classes="fr-pt-1w"
    ) as send_area:
        # textbox = gr.Textbox(
        with gr.Row(elem_classes="items-start"):
            textbox = FrInput(
                elem_id="main-textbox",
                show_label=False,
                lines=1,
                placeholder="Ecrivez votre premier message aux modèles ici",
                max_lines=7,
                # elem_classes="inline-block fr-col-12 fr-col-md-10",
                container=True,
                autofocus=True,
                # autoscroll=True
            )
            send_btn = gr.Button(
                interactive=False,
                # scale=1,
                value="Envoyer",
                # icon="assets/dsfr/icons/system/arrow-up-line.svg",
                elem_id="send-btn",
                elem_classes="grow-0 purple-btn",
            )
        with gr.Row(elem_classes="fr-grid-row fr-grid-row--center"):
            conclude_btn = gr.Button(
                value="Voter pour votre IA favorite",
                elem_classes="fr-col-12 fr-col-md-5 purple-btn fr-mt-1w",
                visible=False,
                interactive=False,
            )

    with gr.Column(
        # h-screen
        visible=False,
        elem_classes="fr-container fr-px-md-16w fr-px-0 min-h-screen fr-pt-4w",
        elem_id="vote-area",
    ) as vote_area:
        gr.HTML(
            value="""
            <h3 class="text-center fr-mt-2w fr-mb-1v">Votez pour découvrir l'identité des modèles</h3>
            <p class="text-center text-grey fr-text--sm">L'ensemble des votes permet d’améliorer les modèles d'IA</p>""",
        )

        which_model_radio = CustomRadioCard(
            elem_classes="justify-center",
            # elem_classes="show-radio self-center justify-center",
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

        with gr.Row(
            visible=False,
            elem_id="supervote-area",
            elem_classes="fr-grid-row fr-grid-row--gutters gap-0 fr-mt-8w fr-mb-md-16w fr-mb-16w",
        ) as supervote_area:

            # with gr.Column():
            with gr.Column(
                elem_classes="fr-col-12 fr-col-md-6 fr-ml-md-n1w fr-mr-md-1w bg-white rounded-corners"
            ):

                gr.HTML(
                    value="""<p><svg class="inline" width='26' height='26'><circle cx='13' cy='13' r='12' fill='#A96AFE' stroke='none'/></svg> <strong>Modèle A</strong></p>
    <p><strong>Comment qualifiez-vous ses réponses ?</strong></p>"""
                )

                positive_a = gr.CheckboxGroup(
                    elem_classes="thumb-up-icon flex checkboxes",
                    show_label=False,
                    choices=[
                        ("Utiles", "useful"),
                        ("Complètes", "complete"),
                        ("Créatives", "creative"),
                        ("Mise en forme claire", "clear-formatting"),
                    ],
                )

                negative_a = gr.CheckboxGroup(
                    elem_classes="thumb-down-icon flex checkboxes",
                    show_label=False,
                    choices=[
                        ("Hallucinations", "hallucinations"),
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

            # with gr.Column():
            with gr.Column(
                elem_classes="fr-col-12 fr-col-md-6 fr-ml-md-3w fr-mr-md-n3w bg-white rounded-corners"
            ):

                gr.HTML(
                    value="""<p><svg class="inline" width='26' height='26'><circle cx='13' cy='13' r='12' fill='#ff9575' stroke='none'/></svg> <strong>Modèle B</strong></p>
    <p><strong>Comment qualifiez-vous ses réponses ?</strong></p>"""
                )

                positive_b = gr.CheckboxGroup(
                    elem_classes="thumb-up-icon flex checkboxes",
                    show_label=False,
                    choices=[
                        ("Utiles", "useful"),
                        ("Complètes", "complete"),
                        ("Créatives", "creative"),
                        ("Mise en forme claire", "clear-formatting"),
                    ],
                )

                negative_b = gr.CheckboxGroup(
                    elem_classes="thumb-down-icon flex checkboxes",
                    show_label=False,
                    choices=[
                        ("Hallucinations", "hallucinations"),
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
            comments_link = gr.Button(elem_classes="link fr-mt-2w", value="Ajouter des détails")

    with gr.Column(
        elem_classes="fr-container--fluid fr-py-2w fr-grid-row fr-grid-row--center",
        elem_id="buttons-footer",
        visible=False,
    ) as buttons_footer:

        supervote_send_btn = gr.Button(
            elem_classes="purple-btn fr-mx-auto fr-col-10 fr-col-md-4",
            value="Découvrir l'identité des deux IA",
            interactive=False,
        )

    with gr.Column(
        elem_id="reveal-screen", visible=False, elem_classes="min-h-screen fr-pt-4w"
    ) as reveal_screen:

        results_area = gr.HTML(visible=True, elem_classes="fr-container")

        with gr.Column(visible=True, elem_id="feedback-row") as feedback_row:
            # dsfr: This should just be a normal link
            # feedback_btns =
            gr.HTML(
                elem_classes="fr-container text-center",
                value="""
                <a class="btn purple-btn fr-my-2w" href="../arene/?cgu_acceptees">Discuter avec deux nouvelles IA</a><br />
                <a class="fr-mx-auto fr-mb-4w" href="../modeles">Découvrir la liste des IA</a>
            """,
            )

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
