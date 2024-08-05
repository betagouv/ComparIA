"""
Chatbot Arena (battle) tab.
Users chat with two anonymous models.
"""

# import json
# import time

import gradio as gr
import numpy as np
import requests

from fastchat.constants import (
    MODERATION_MSG,
    CONVERSATION_LIMIT_MSG,
    SLOW_MODEL_MSG,
    CONVERSATION_TURN_LIMIT,
)

# from fastchat.model.model_adapter import get_conversation_template

from languia.block_conversation import (
    # TODO: to import/replace State and bot_response?
    ConversationState,
    bot_response,
)

from languia.config import logger


from languia.utils import (
    get_ip,
    get_battle_pair,
    build_reveal_html,
    start_screen_html,
    header_html,
    stepper_html,
    vote_last_response,
    get_model_extra_info,
    count_output_tokens,
    get_llm_impact,
    running_eq,
)

from custom_components.frbutton.backend.gradio_frbutton import FrButton
from custom_components.frinput.backend.gradio_frinput import FrInput


from languia import config

from languia.config import (
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
    SAMPLING_WEIGHTS,
    BATTLE_TARGETS,
    SAMPLING_BOOST_MODELS,
    outage_models,
)

# // Enable navigation prompt
# window.onbeforeunload = function() {
#     return true;
# };
# // Remove navigation prompt
# window.onbeforeunload = null;

app_state = gr.State()

from themes.dsfr import DSFR

with gr.Blocks(
    title="LANGU:IA – L'arène francophone de comparaison de modèles conversationnels",
    theme=DSFR(),
    css=config.css,
    head=config.arena_head_js,
    analytics_enabled=False,
    # Doesn't work with uvicorn
    # delete_cache=(1, 1) if config.debug else None,
    # Dirty hack for accepting ToS
    js=config.arena_js,
) as demo:
    # A tester
    # conversations_state = [ConversationState() for _ in range(config.num_sides)]
    conversations_state = [gr.State() for _ in range(config.num_sides)]
    # model_selectors = [None] * num_sides
    # TODO: allow_flagging?
    chatbots = [None] * config.num_sides

    # TODO: check cookies on load!
    # tos_cookie = check_for_tos_cookie(request)
    # if not tos_cookie:

    # gr.HTML(elem_id="header-placeholder")
    header = gr.HTML(start_screen_html, elem_id="header-html")

    with gr.Column(elem_classes="fr-container") as start_screen:

        start_arena_btn = gr.Button(
            value="C'est parti",
            scale=0,
            # TODO: à centrer
            elem_id="start_arena_btn",
            elem_classes="fr-btn fr-mx-auto",
            interactive=False,
        )

    # with gr.Row(elem_id="stepper-row", elem_classes="fr-pb-2w") as stepper_row:
    # with gr.Row(elem_id="stepper-row", elem_classes="raised fr-pb-2w") as stepper_row:
    stepper_block = gr.HTML(
        stepper_html("Choix du mode de conversation", 1, 4),
        elem_id="stepper-html",
        visible=False,
    )

    with gr.Column(
        visible=False, elem_id="mode-screen", elem_classes="fr-container"
    ) as mode_screen:
        gr.HTML(
            """
        <div class="fr-notice fr-notice--info"> 
            <div class="fr-container">
                    <div class="fr-notice__body mission" >
                        <p class="fr-notice__title mission">Discutez d’un sujet qui vous intéresse puis évaluez les réponses des modèles.</p>
                    </div>
            </div>
        </div>"""
        )
        gr.HTML(
            """<div class="text-center fr-mt-4w fr-mb-2w fr-grid-row fr-grid-row--center"><h4 class="fr-mb-1v fr-col-12">Comment voulez-vous commencer la conversation ?</h4>
            <p class="fr-col-12"><em>(Sélectionnez un des deux modes)</em></p></div>"""
        )
        with gr.Row(
            elem_classes="fr-grid-row fr-grid-row--gutters fr-grid-row--center fr-col-12"
        ):
            mode_selection_classes = "fr-col-12 fr-col-md-4 fr-p-4w"
            free_mode_btn = FrButton(
                custom_html="""<h4>Mode libre</h4><p class="fr-text--lg">Ecrivez directement aux modèles, discutez du sujet que vous voulez</p>""",
                elem_id="free-mode",
                elem_classes="fr-ml-auto " + mode_selection_classes,
                icon="assets/extra-artwork/conclusion.svg",
            )
            guided_mode_btn = FrButton(
                elem_classes="fr-mr-auto " + mode_selection_classes,
                elem_id="guided-mode",
                custom_html="""<h4>Mode inspiré</h4><p class="fr-text--lg">Vous n'avez pas d'idée ? Découvrez une série de thèmes inspirants</p>""",
                icon="assets/extra-artwork/innovation.svg",
            )

        with gr.Column(
            elem_id="guided-area",
            # elem_classes="fr-grid-row" messes with visible=False...
            # elem_classes="fr-grid-row fr-grid-row--center",
            visible=False,
        ) as guided_area:
            gr.Markdown(
                elem_classes="text-center fr-mt-4w fr-mb-2w",
                value="##### Sélectionnez un thème que vous aimeriez explorer :",
            )
            # fr-col-12 fr-col-sm-8 fr-col-md-6 fr-col-lg-4 fr-col-xl-2
            with gr.Row(elem_classes="radio-tiles"):
                maniere = FrButton(
                    value="maniere",
                    custom_html="""<span class="fr-badge fr-badge--purple-glycine">Style</span><p>Ecrire à la manière d'un romancier ou d'une romancière</p>""",
                )
                registre = FrButton(
                    value="registre",
                    custom_html="""<span class="fr-badge fr-badge--purple-glycine">Style</span><p>Transposer en registre familier, courant, soutenu…</p>""",
                )
                creativite_btn = FrButton(
                    value="creativite",
                    custom_html="""<span class="fr-badge fr-badge--green-tilleul-verveine">Créativité</span><p>Jeux de mots, humour et expressions</p>""",
                )
            with gr.Row(elem_classes="radio-tiles"):
                pedagogie = FrButton(
                    value="pedagogie",
                    custom_html="""<span class="fr-badge fr-badge--blue-cumulus">Pédagogie</span><p>Expliquer simplement un concept</p>""",
                )
                regional = FrButton(
                    value="regional",
                    custom_html="""<span class="fr-badge fr-badge--yellow-moutarde">Diversité</span><p>Parler en Occitan, Alsacien, Basque, Picard…</p>""",
                )
                variete = FrButton(
                    value="variete",
                    custom_html="""<span class="fr-badge fr-badge--yellow-moutarde">Diversité</span><p>Est-ce différent en Québécois, Belge, Suisse, Antillais…</p>""",
                )

    # with gr.Column(elem_id="send-area", elem_classes="fr-grid-row", visible=False) as send_area:
    with gr.Column(elem_id="send-area", visible=False) as send_area:
        with gr.Row(elem_classes="fr-grid-row"):
            # textbox = gr.Textbox(
            textbox = FrInput(
                elem_id="main-textbox",
                show_label=False,
                lines=1,
                placeholder="Ecrivez votre premier message à l'arène ici",
                max_lines=7,
                # TODO: raise fr-col-md to 10 ?
                elem_classes="fr-col-12 fr-col-md-9",
                container=False,
                # not working
                # autofocus=True
            )
            send_btn = gr.Button(
                interactive=False,
                value="Envoyer",
                elem_id="send-btn",
                elem_classes="fr-btn fr-col-6 fr-col-md-1",
            )
            # FIXME: visible=false not working?
            # retry_btn = gr.Button(
            #     icon="assets/dsfr/icons/system/refresh-line.svg",
            #     value="",
            #     elem_classes="icon-blue fr-btn fr-btn--secondary",
            #     # elem_classes="fr-icon-refresh-line",
            #     visible=False,
            #     # render=False,
            #     scale=1,
            # )
        with gr.Row(elem_classes="fr-grid-row fr-grid-row--center"):
            # TODO: griser le bouton "Terminer et donner mon avis" tant que les LLM n'ont pas fini d'écrire
            conclude_btn = gr.Button(
                value="Terminer et donner mon avis",
                elem_classes="fr-btn fr-col-12 fr-col-md-4",
                visible=False,
                interactive=False,
            )

    with gr.Group(elem_id="chat-area", visible=False) as chat_area:
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

    with gr.Column(visible=False, elem_classes="fr-container") as vote_area:
        gr.Markdown(elem_classes="fr-mt-2w", value="## Quel modèle avez-vous préféré ?")
        with gr.Row():
            which_model_radio = gr.Radio(
                elem_classes="radio-tiles bolder",
                show_label=False,
                choices=[
                    ("Modèle A", "leftvote"),
                    ("Modèle B", "rightvote"),
                    ("Aucun des deux", "bothbad"),
                ],
            )
            # leftvote_btn = gr.Button(value="👈  A est mieux")
            # rightvote_btn = gr.Button(value="👉  B est mieux")
            # # tie_btn = gr.Button(value="🤝  Les deux se valent")
            # bothbad_btn = gr.Button(value="👎  Aucun des deux")

        # with gr.Column(visible=False, elem_classes="fr-container") as supervote_area:
        with gr.Column(visible=False) as supervote_area:

            # TODO: render=false?
            # TODO: move to another file?
            with gr.Column() as positive_supervote:
                gr.Markdown(
                    value="### Pourquoi ce choix de modèle ?\nSélectionnez autant de préférences que vous souhaitez"
                )
                # TODO: checkboxes tuple
                ressenti_checkbox = gr.CheckboxGroup(
                    [
                        "Impressionné·e",
                        "Complet",
                        "Facile à comprendre",
                        "Taille des réponses adaptées",
                    ],
                    label="ressenti",
                    show_label=False,
                    info="Ressenti général",
                )
                pertinence_checkbox = gr.CheckboxGroup(
                    [
                        "Consignes respectées",
                        "Cohérent par rapport au contexte",
                        "Le modèle ne s'est pas trompé",
                    ],
                    label="pertinence",
                    show_label=False,
                    info="Pertinence des réponses",
                )
                comprehension_checkbox = gr.CheckboxGroup(
                    [
                        "Syntaxe adaptée",
                        "Richesse du vocabulaire",
                        "Utilisation correcte des expressions",
                    ],
                    label="comprehension",
                    show_label=False,
                    info="Compréhension et expression",
                )
                originalite_checkbox = gr.CheckboxGroup(
                    ["Créatif", "Expressif", "Drôle"],
                    label="originalite",
                    info="Créativité et originalité",
                    show_label=False,
                )

            # TODO: render=false?
            # TODO: move to another file
            with gr.Column() as negative_supervote:
                gr.Markdown(
                    value="### Pourquoi êtes-vous insatisfait·e des deux modèles ?\nSélectionnez autant de préférences que vous souhaitez"
                )
                ressenti_checkbox = gr.CheckboxGroup(
                    [
                        "Trop court",
                        "Trop long",
                        "Pas utile",
                        "Nocif ou offensant",
                    ],
                    label="ressenti",
                    info="Ressenti général",
                    show_label=False,
                )
                pertinence_checkbox = gr.CheckboxGroup(
                    [
                        "Incohérentes par rapport au contexte",
                        "Factuellement incorrectes",
                        "Imprécises",
                    ],
                    label="pertinence",
                    info="Pertinence des réponses",
                    show_label=False,
                )
                comprehension_checkbox = gr.CheckboxGroup(
                    [
                        "Faible qualité de syntaxe",
                        "Pauvreté du vocabulaire",
                        "Mauvaise utilisation des expressions",
                    ],
                    label="comprehension",
                    info="Compréhension et expression",
                    show_label=False,
                )
                originalite_checkbox = gr.CheckboxGroup(
                    ["Réponses banales", "Réponses superficielles"],
                    label="originalite",
                    info="Créativité et originalité",
                    show_label=False,
                )

            supervote_checkboxes = [
                ressenti_checkbox,
                pertinence_checkbox,
                comprehension_checkbox,
                originalite_checkbox,
            ]

            comments_text = FrInput(
                # elem_classes="fr-input",
                label="Détails supplémentaires",
                show_label=True,
                # TODO:
                # info=,
                # autofocus=True,
                placeholder="Ajoutez plus de précisions ici",
            )

    with gr.Column(
        elem_classes="arena-footer fr-container--fluid", visible=False
    ) as buttons_footer:
        with gr.Row(elem_classes="fr-grid-row fr-container fr-mt-4w"):
            return_btn = gr.Button(
                elem_classes="fr-btn fr-btn--secondary fr-col-12 fr-col-md-1",
                value="Retour",
            )
            final_send_btn = gr.Button(
                elem_classes="fr-btn fr-col-12 fr-col-md-3 fr-col-offset-md-2",
                value="Envoyer mes préférences",
                interactive=False,
            )

    results_area = gr.HTML(visible=False, elem_classes="fr-container")

    with gr.Row(visible=False) as feedback_row:
        # dsfr: This should just be a normal link...
        # feedback_btns =
        gr.HTML(
            value="""
            <div class="fr-grid-row fr-grid-row--center fr-grid-row--gutters">
            <a class="fr-btn" href="https://adtk8x51mbw.eu.typeform.com/to/kiPl3JAL" >Donner mon avis sur l'arène</a>
            <a class="fr-btn fr-btn--secondary" href="../modeles">Liste des modèles</a>
            </div>
        """
        )

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

    from languia.controllers import register_listeners

    register_listeners()

