"""
LANGU:IA's main code
Users chat with two anonymous models.
"""

import gradio as gr

# from gradio_modal import Modal

from languia.utils import header_html, welcome_modal_html

# from custom_components.frbutton.backend.gradio_frbutton import FrButton
from custom_components.customradiocard.backend.gradio_customradiocard import (
    CustomRadioCard,
)
from custom_components.frinput.backend.gradio_frinput import FrInput
from custom_components.frslider.backend.gradio_frslider import FrSlider

# from custom_components.customslider.backend.gradio_customslider import CustomSlider


from languia import config

# // Enable navigation prompt
# window.onbeforeunload = function() {
#     return true;
# };
# // Remove navigation prompt
# window.onbeforeunload = null;

app_state = gr.State()

from themes.dsfr import DSFR

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
    # A tester
    # conversations = [ConversationState() for _ in range(config.num_sides)]
    conversations = [gr.State() for _ in range(config.num_sides)]
    # model_selectors = [None] * num_sides

    # TODO: check cookies on load!
    # tos_cookie = check_for_tos_cookie(request)
    # if not tos_cookie:
    welcome_modal = gr.HTML(welcome_modal_html, elem_id="welcome-modal-html")

    # gr.HTML(elem_id="header-placeholder")
    header = gr.HTML(header_html, elem_id="header-html")

    with gr.Column(elem_id="mode-screen", elem_classes="fr-container") as mode_screen:

        title = gr.HTML(
            elem_classes="text-center fr-mt-6w fr-mb-1w",
            value="""<h3>Comment puis-je vous aider aujourd'hui ?</h3>""",
        )

        guided_cards = CustomRadioCard(
            show_label=False,
            # elem_classes="fr-grid-row fr-grid-row--gutters fr-grid-row--center",
            # elem_classes="fr-container",
            choices=[
                (
                    """<div class="min-h-28"><span class="fr-badge fr-badge--sm fr-badge--green-tilleul-verveine fr-badge--icon-left fr-icon-booklet">Expression</span><p>Raconter une histoire, expliquer un concept, obtenir un résumé...</p></div>""",
                    "expression",
                ),
                (
                    """<div class="min-h-28"><span class="fr-badge fr-badge--sm fr-badge--blue-cumulus fr-badge--icon-left fr-icon-translate-2 fr-mb-1w ">Langues</span><p>M’exprimer en langue régionale ou dans une langue étrangère</p></div>""",
                    "langues",
                ),
                (
                    """<div class="min-h-28"><span class="fr-badge fr-badge--sm fr-badge--yellow-moutarde fr-badge--icon-left fr-icon-lightbulb fr-mb-1w">Vie pratique</span><p>Obtenir un plan personnalisé : bien être, sport, nutrition...</p></div>""",
                    "conseils",
                ),
                (
                    """<div class="min-h-28"><span class="fr-badge fr-badge--sm fr-badge--purple-glycine fr-badge--icon-left fr-icon-bike fr-mb-1w">Loisirs</span><p>Organiser mon temps libre : voyages, cuisine, livres, musiques...</p></div>""",
                    "loisirs",
                ),
                (
                    """<div class="min-h-28"><span class="fr-badge fr-badge--sm fr-badge--orange-terre-battue fr-badge--icon-left fr-icon-draft fr-mb-1w">Administratif</span><p>Rédiger un document : résiliation d’un bail, email de réclamation</p></div>""",
                    "administratif",
                ),
                (
                    """<div class="min-h-28"><span class="fr-badge fr-badge--sm fr-badge--blue-ecume fr-badge--icon-left fr-icon-briefcase">Vie professionnelle</span><p>Générer des idées, rédiger une note, corriger mes travaux...</p></div>""",
                    "vie-professionnelle",
                ),
            ],
        )
        free_mode_btn = gr.Button(
            scale=1,
            elem_id="free-mode",
            value="Je veux écrire sur mon propre sujet",
            elem_classes="fr-btn fr-btn--secondary fr-mx-auto fr-mt-8w fr-mb-4w",
        )

    with gr.Group(
        elem_id="chat-area",
        visible=False,
        elem_classes="fr-mb-10w fr-mb-md-0",
    ) as chat_area:
        label = "Modèles A et B"

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
            label=label,
            # UserWarning: show_label has no effect when container is False.
            show_label=False,
            container=False,
            elem_classes="chatbot",
            # Should we show it?
            show_copy_button=False,
            # autoscroll=True
        )

    with gr.Column(elem_id="send-area", visible=False) as send_area:
        # textbox = gr.Textbox(
        with gr.Column(elem_classes="inline-block"):
            textbox = FrInput(
                elem_id="main-textbox",
                show_label=False,
                lines=1,
                placeholder="Ecrivez votre premier message aux modèles ici",
                max_lines=7,
                elem_classes="inline-block fr-col-12 fr-col-md-10 bg-white",
                container=False,
                autofocus=True,
                # autoscroll=True
            )
            send_btn = gr.Button(
                interactive=False,
                scale=1,
                value="Envoyer",
                elem_id="send-btn",
                elem_classes="inline-block fr-btn fr-ml-3v",
            )
        shuffle_btn = gr.Button(
            scale=1,
            size="sm",
            elem_classes="fr-btn fr-btn--tertiary small-icon fr-mx-auto",
            interactive=False,
            value="Générer un autre message",
            icon="assets/extra-icons/shuffle.svg",
        )

        with gr.Row(elem_classes="fr-grid-row fr-grid-row--center"):
            conclude_btn = gr.Button(
                value="Voter pour votre IA favorite",
                elem_classes="fr-btn fr-col-12 fr-col-md-5",
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
            <h3 class="text-center fr-mt-2w fr-mb-1v">Votez pour découvrir leurs identités</h3>
            <p class="text-center text-grey fr-text--sm">Votre vote permet d’améliorer les réponses des deux IA</p>""",
        )

        which_model_radio = CustomRadioCard(
            choices=[
                (
                    """<span class="fr-badge fr-badge--no-icon fr-badge--info self-center">Modèle A</span>""",
                    "model-a",
                ),
                (
                    """<span class="fr-badge fr-badge--green-tilleul-verveine self-center">Modèle B</span>""",
                    "model-b",
                ),
            ],
            show_label=False,
        )
        both_equal_link = gr.Button(
            elem_id="both-equal-link",
            elem_classes="fr-btn fr-btn--secondary fr-mx-auto",
            value="Les deux se valent",
        )

        with gr.Column(
            visible=False, elem_classes="fr-container fr-mt-8w fr-mb-md-16w fr-mb-16w"
        ) as supervote_area:

            why_vote = gr.HTML(
                """<h4>Pourquoi préférez-vous ce modèle d'IA ?</h4><p class="text-grey">Attribuez pour chaque question une note entre 1 et 5 sur le modèle que vous venez de sélectionner</p>""",
                elem_classes="text-center",
            )

            with gr.Column(elem_classes="fr-container fr-px-0 fr-px-md-16w"):
                relevance_slider = FrSlider(
                    value=-1,
                    range_labels=["Pas du tout d'accord", "Tout à fait d'accord"],
                    minimum=1,
                    maximum=5,
                    step=1,
                    label="Les réponses étaient pertinentes",
                    info="Critères : réponses utiles, correctes factuelles, précises",
                    elem_classes="fr-mb-4w",
                )
                form_slider = FrSlider(
                    value=-1,
                    range_labels=["Pas du tout d'accord", "Tout à fait d'accord"],
                    minimum=1,
                    maximum=5,
                    step=1,
                    label="Les réponses étaient simples à lire",
                    info="Critères : mise en forme et longueur des réponses adaptées",
                    elem_classes="fr-my-4w",
                )
                style_slider = FrSlider(
                    elem_classes="fr-my-4w",
                    range_labels=["Pas du tout d'accord", "Tout à fait d'accord"],
                    value=-1,
                    minimum=1,
                    maximum=5,
                    step=1,
                    label="Le style de la réponse était adapté",
                    info="Critères : registre de langue, vocabulaire, orthographe",
                )
                supervote_sliders = [relevance_slider, form_slider, style_slider]

                comments_text = FrInput(
                    elem_classes="big-label",
                    label="Détails supplémentaires",
                    show_label=True,
                    lines=3,
                    placeholder="Ajoutez des précisions sur ce qui vous a plus et moins plu",
                )

    with gr.Column(
        elem_classes="fr-container--fluid fr-py-2w", elem_id="buttons-footer", visible=False
    ) as buttons_footer:

            supervote_send_btn = gr.Button(
                elem_classes="fr-btn fr-mx-auto",
                value="Découvrir l'identité des deux IA",
                interactive=False,
            )

    with gr.Column(
        elem_id="reveal-screen", visible=False, elem_classes="min-h-screen fr-pt-4w"
    ) as reveal_screen:

        results_area = gr.HTML(visible=True, elem_classes="fr-container")

        with gr.Column(visible=True, elem_id="feedback-row") as feedback_row:
            # dsfr: This should just be a normal link...
            # feedback_btns =
            gr.HTML(
                elem_classes=" fr-container",
                value="""
                <div class="fr-py-4w">
                <a class="block fr-btn fr-mx-auto fr-mb-2w" href="../arene/?cgu_acceptees">Discuter avec deux nouvelles IA</a>
                <a class="block fr-btn fr-btn--secondary fr-mx-auto" href="../modeles">Découvrir la liste des IA</a>
                </div>
            """
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
