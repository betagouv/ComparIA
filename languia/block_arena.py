"""
LANGU:IA's main code
Users chat with two anonymous models.
"""

import gradio as gr

from gradio_modal import Modal

from languia.utils import stepper_html, header_html, welcome_modal_html

# from custom_components.frbutton.backend.gradio_frbutton import FrButton
from custom_components.customradiocard.backend.gradio_customradiocard import (
    CustomRadioCard,
)
from custom_components.frinput.backend.gradio_frinput import FrInput
from custom_components.frslider.backend.gradio_frslider import FrSlider
from custom_components.customslider.backend.gradio_customslider import CustomSlider


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
    # js=config.arena_js,
    js=None,
    # Doesn't work with uvicorn
    # delete_cache=(1, 1) if config.debug else None,
) as demo:
    # A tester
    # conversations = [ConversationState() for _ in range(config.num_sides)]
    conversations = [gr.State() for _ in range(config.num_sides)]
    # model_selectors = [None] * num_sides
    # TODO: allow_flagging?
    chatbots = [None] * config.num_sides

    # TODO: check cookies on load!
    # tos_cookie = check_for_tos_cookie(request)
    # if not tos_cookie:
    welcome_modal = gr.HTML(welcome_modal_html, elem_id="welcome-modal-html")

    # gr.HTML(elem_id="header-placeholder")
    header = gr.HTML(header_html, elem_id="header-html")

    stepper_block = gr.HTML(
        stepper_html("Bienvenue ! Comment puis-je vous aider aujourd'hui ?", 1, 4),
        elem_id="stepper-html",
        visible=False,
    )

    with gr.Column(
        visible=False, elem_id="mode-screen", elem_classes="fr-container"
    ) as mode_screen:

        guided_cards = CustomRadioCard(
            show_label=False,
            # elem_classes="fr-grid-row fr-grid-row--gutters fr-grid-row--center",
            # elem_classes="fr-container",
            choices=[
                (
                    """<span class="fr-badge fr-badge--sm fr-badge--green-tilleul-verveine fr-badge--icon-left fr-icon-booklet">Expression</span><p>Raconter une histoire, expliquer un concept, obtenir un résumé...</p>""",
                    "expression",
                ),
                (
                    """<span class="fr-badge fr-badge--sm fr-badge--blue-cumulus fr-badge--icon-left fr-icon-translate-2 fr-mb-1w ">Langues</span><p>M’exprimer en langue régionale ou dans une langue étrangère</p>""",
                    "langues",
                ),
                (
                    """<span class="fr-badge fr-badge--sm fr-badge--yellow-moutarde fr-badge--icon-left fr-icon-lightbulb fr-mb-1w">Conseils</span><p>Obtenir un plan personnalisé : bien être, sport, nutrition...</p>""",
                    "conseils",
                ),
                (
                    """<span class="fr-badge fr-badge--sm fr-badge--purple-glycine fr-badge--icon-left fr-icon-bike fr-mb-1w">Loisirs</span><p>Organiser mon temps libre : voyages, cuisine, livres, musiques...</p>""",
                    "loisirs",
                ),
                (
                    """<span class="fr-badge fr-badge--sm fr-badge--orange-terre-battue fr-badge--icon-left fr-icon-draft fr-mb-1w">Administratif</span><p>Rédiger un document : résiliation d’un bail, email de réclamation</p>""",
                    "administratif",
                ),
                (
                    """<span class="fr-badge fr-badge--sm fr-badge--blue-ecume fr-badge--icon-left fr-icon-briefcase">Vie professionnelle</span><p>Générer des idées, rédiger une note, corriger mes travaux...</p>""",
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
                value="Terminer et donner mon avis",
                elem_classes="fr-btn fr-col-12 fr-col-md-4",
                visible=False,
                interactive=False,
            )

            retry_modal_btn = gr.Button(
                value="",
                elem_id="retry-modal-btn",
                elem_classes="fr-btn fr-btn--secondary fr-icon-refresh-line fr-col-1",
                #  icon="assets/dsfr/icons/system/refresh-line.svg",
                scale=1,
                visible=False,
            )

    with gr.Group(
        elem_id="chat-area",
        visible=False,
        elem_classes="fr-mb-10w fr-pb-16w fr-mb-md-0",
    ) as chat_area:
        with gr.Row():
            for i in range(config.num_sides):
                label = "Modèle A" if i == 0 else "Modèle B"
                with gr.Column():
                    # {likeable}
                    # placeholder
                    #         placeholder
                    # a placeholder message to display in the chatbot when it is empty. Centered vertically and horizontally in the Chatbot. Supports Markdown and HTML.
                    chatbots[i] = gr.Chatbot(
                        # TODO:
                        # type="messages",
                        elem_id=f"chatbot-{i}",
                        # min_width=
                        height="100%",
                        # Doesn't show because it always has at least our message
                        # Note: supports HTML, use it!
                        placeholder="<em>Veuillez écrire au modèle</em>",
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
                    )

    with gr.Column(
        visible=False, elem_classes="fr-container fr-mb-12w fr-px-md-16w fr-px-0"
    ) as vote_area:
        gr.HTML(
            value="""
        <div class="fr-notice fr-notice--info"> 
            <div class="fr-container">
                <div class="fr-notice__body mission">
                    <p class="fr-notice__title mission">Des réponses détaillées de votre part permettent à la recherche d’améliorer les réponses des futurs modèles sur des enjeux linguistiques et culturels.</p>
                </div>
            </div>
        </div>
            <h3 class="text-center fr-mt-2w">Quel modèle avez-vous préféré ?*</h3>""",
        )

        which_model_radio = CustomSlider(
            minimum=-1.5,
            maximum=+1.5,
            value=-3,
            step=1,
            show_label=False,
            extrema=["Modèle A", "Modèle B"],
            range_labels=[
                "Je préfère le modèle A",
                "Le modèle A est un peu mieux",
                "Le modèle B est un peu mieux",
                "Je préfère le modèle B",
            ],
        )

        with gr.Column(
            visible=False, elem_classes="fr-container fr-mb-md-6w fr-mb-16w"
        ) as supervote_area:

            why_vote = gr.HTML(
                """<h4>Pourquoi préférez-vous ce modèle ?</h4><p class="text-grey">Attribuez pour chaque question une note entre 1 et 5 sur le modèle que vous venez de sélectionner</p>""",
                elem_classes="text-center",
            )

            with gr.Column(elem_classes="fr-container fr-px-0 fr-px-md-16w"):
                relevance_slider = FrSlider(
                    value=-1,
                    range_labels=["Pas du tout d'accord", "Tout à fait d'accord"],
                    minimum=1,
                    maximum=5,
                    step=1,
                    label="Les réponses étaient-elles pertinentes ?",
                    info="Critères : réponses utiles, correctes factuelles, précises",
                    elem_classes="fr-my-4w",
                )
                form_slider = FrSlider(
                    value=-1,
                    range_labels=["Pas du tout d'accord", "Tout à fait d'accord"],
                    minimum=1,
                    maximum=5,
                    step=1,
                    label="Les réponses étaient-elles simples à lire ?",
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
                    label="Le style de la réponse était-il adapté ?",
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
        elem_classes="fr-container--fluid", elem_id="buttons-footer", visible=False
    ) as buttons_footer:
        with gr.Row(elem_classes="fr-grid-row fr-container fr-my-2w"):
            return_btn = gr.Button(
                elem_classes="fr-btn fr-btn--secondary fr-col-12 fr-col-md-1",
                value="Retour",
            )
            supervote_send_btn = gr.Button(
                elem_classes="fr-btn fr-col-12 fr-col-md-4 fr-col-offset-md-3",
                value="Envoyer mes préférences",
                interactive=False,
            )

    results_area = gr.HTML(visible=False, elem_classes="fr-container")

    with gr.Row(visible=False, elem_id="feedback-row") as feedback_row:
        # dsfr: This should just be a normal link...
        # feedback_btns =
        gr.HTML(
            value="""
            <div class="fr-grid-row fr-grid-row--center fr-py-4w">
            <a class="fr-btn fr-btn--secondary fr-ml-2w" href="../modeles">Liste des modèles</a>
            </div>
        """
        )

    with Modal(elem_id="quiz-modal") as quiz_modal:
        gr.Markdown(
            """
                    ### Dernière étape
                    Ces quelques informations sur votre profil permettront à la recherche d’affiner les réponses des futurs modèles.
                    """
        )
        profession = gr.Dropdown(
            choices=[
                "Agriculteur",
                "Artisan, commerçant et chef d'entreprise",
                "Cadre et profession intellectuelle supérieure",
                "Profession intermédiaire",
                "Étudiant",
                "Employé",
                "Ouvrier",
                "Retraité",
                "Sans emploi",
                "Ne se prononce pas",
            ],
            label="Catégorie socioprofessionnelle",
        )
        age = gr.Dropdown(
            choices=[
                "Moins de 18 ans",
                "Entre 18 et 24 ans",
                "Entre 25 et 34 ans",
                "Entre 35 et 44 ans",
                "Entre 45 et 54 ans",
                "Entre 55 et 64 ans",
                "Plus de 64 ans",
                "Ne se prononce pas",
            ],
            label="Tranche d'âge",
        )
        gender = gr.Dropdown(
            choices=["Femme", "Homme", "Autre", "Ne se prononce pas"], label="Genre"
        )
        chatbot_use = gr.Dropdown(
            choices=[
                "Tous les jours",
                "Toutes les semaines",
                "Une fois par mois",
                "Moins d’une fois par mois",
                "Jamais",
                "Ne se prononce pas",
            ],
            label="Fréquence d’utilisation d’assistants conversationnels",
        )
        with gr.Row(elem_classes="fr-grid-row fr-grid-row--gutters fr-grid-row--right"):
            skip_poll_btn = gr.Button("Passer", elem_classes="fr-btn fr-btn--secondary")
            send_poll_btn = gr.Button("Envoyer", elem_classes="fr-btn")

    # TODO: get rid
    temperature = gr.Slider(
        visible=False,
        # minimum=0.0,
        # maximum=1.0,
        value=0.7,
        # step=0.1,
        interactive=False,
        label="Temperature",
    )
    top_p = gr.Slider(
        visible=False,
        minimum=0.0,
        maximum=1.0,
        value=1.0,
        step=0.1,
        interactive=False,
        label="Top P",
    )
    max_output_tokens = gr.Slider(
        visible=False,
        minimum=16,
        maximum=2048,
        value=1024,
        step=64,
        interactive=False,
        label="Max output tokens",
    )

    # Modals
    with Modal(elem_id="retry-modal") as retry_modal:
        gr.HTML(
            """<h1 class="fr-modal__title"><span class="fr-icon-arrow-right-line fr-icon--lg"></span> Etes-vous sûr·e de quitter sans voter ?</h1>
<p>Vous êtes sur le point de recommencer une nouvelle conversation sans avoir voté sur celle-ci qui est en cours.</p>"""
        )
        with gr.Row():
            close_retry_modal_btn = gr.Button(
                value="Non, annuler", elem_classes="fr-btn fr-btn--secondary", scale=1
            )
            retry_btn = gr.Button(
                value="Oui, recommencer une conversation",
                elem_classes="fr-btn",
                scale=1,
            )

    from languia.listeners import register_listeners

    register_listeners()
