"""
Chatbot Arena (battle) tab.
Users chat with two anonymous models.
"""

import json
import time

import gradio as gr
import numpy as np

from fastchat.constants import (
    MODERATION_MSG,
    CONVERSATION_LIMIT_MSG,
    SLOW_MODEL_MSG,
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
    CONVERSATION_TURN_LIMIT,
    SAMPLING_WEIGHTS,
    BATTLE_TARGETS,
    SAMPLING_BOOST_MODELS,
    OUTAGE_MODELS,
)

# from fastchat.model.model_adapter import get_conversation_template

from fastchat.serve.languia.block_conversation import (
    # TODO: to import/replace State and bot_response?
    ConversationState,
    bot_response,
    get_conv_log_filename,
    get_ip,
    get_model_description_md,
)

from fastchat.serve.languia.actions import vote_last_response

from fastchat.utils import (
    build_logger,
    moderation_filter,
)

from fastchat.serve.languia.utils import get_battle_pair, build_reveal_html, stepper_html

from gradio_frbutton import FrButton
from gradio_frinput import FrInput

logger = build_logger("gradio_web_server_multi", "gradio_web_server_multi.log")

# TODO: move to constants.py or hardcode it
num_sides = 2
enable_moderation = False

anony_names = ["", ""]
models = []

tos_accepted = False


def set_global_vars_anony(enable_moderation_):
    global enable_moderation
    enable_moderation = enable_moderation_


def load_demo_arena(models_, url_params):
    global models
    models = models_

    conversations_state = (None,) * num_sides
    # FIXME: What does it do???
    selector_updates = (
        gr.Markdown(visible=True),
        gr.Markdown(visible=True),
    )

    return conversations_state + selector_updates


def add_text(
    # state0: ConversationState,
    # state1: ConversationState,
    state0: gr.State,
    state1: gr.State,
    # model_selector0: gr.Markdown,
    # model_selector1: gr.Markdown,
    text: gr.Text,
    request: gr.Request,
):
    ip = get_ip(request)
    logger.info(f"add_text (anony). ip: {ip}. len: {len(text)}")
    conversations_state = [state0, state1]
    # model_selectors = [model_selector0, model_selector1]

    # TODO: refacto and put init apart
    # Init conversations_state if necessary
    if conversations_state[0] is None:
        assert conversations_state[1] is None

        model_left, model_right = get_battle_pair(
            models,
            BATTLE_TARGETS,
            OUTAGE_MODELS,
            SAMPLING_WEIGHTS,
            SAMPLING_BOOST_MODELS,
        )
        conversations_state = [
            # NOTE: replacement of gr.State() to ConversationState happens here
            ConversationState(model_name=model_left),
            ConversationState(model_name=model_right),
        ]

    # FIXME: when submitting empty text
    # if len(text) <= 0:
    #     for i in range(num_sides):
    #         conversations_state[i].skip_next = True
    #     return (
    #         # 2 conversations_state
    #         conversations_state
    #         # 2 chatbots
    #         + [x.to_gradio_chatbot() for x in conversations_state]
    #         # text
    #         + [""]
    #         + [visible_row]
    #         # Slow warning
    #         + [""]
    #     )

    model_list = [conversations_state[i].model_name for i in range(num_sides)]
    # turn on moderation in battle mode
    all_conv_text_left = conversations_state[0].conv.get_prompt()
    all_conv_text_right = conversations_state[0].conv.get_prompt()
    all_conv_text = (
        all_conv_text_left[-1000:] + all_conv_text_right[-1000:] + "\nuser: " + text
    )
    flagged = moderation_filter(all_conv_text, model_list, do_moderation=False)
    if flagged:
        logger.info(f"violate moderation (anony). ip: {ip}. text: {text}")
        # overwrite the original text
        text = MODERATION_MSG

    conv = conversations_state[0].conv
    if (len(conv.messages) - conv.offset) // 2 >= CONVERSATION_TURN_LIMIT:
        logger.info(f"conversation turn limit. ip: {get_ip(request)}. text: {text}")
        for i in range(num_sides):
            conversations_state[i].skip_next = True
            # FIXME: fix return value
        return (
            # 2 conversations_state
            conversations_state
            # 2 chatbots
            + [x.to_gradio_chatbot() for x in conversations_state]
            # text
            + [CONVERSATION_LIMIT_MSG]
            + [gr.update(visible=True)]
        )

    text = text[:BLIND_MODE_INPUT_CHAR_LEN_LIMIT]  # Hard cut-off
    # TODO: what do?
    for i in range(num_sides):
        # post_processed_text = _prepare_text_with_image(conversations_state[i], text, csam_flag=False)
        post_processed_text = text
        conversations_state[i].conv.append_message(
            conversations_state[i].conv.roles[0], post_processed_text
        )
        conversations_state[i].conv.append_message(
            conversations_state[i].conv.roles[1], None
        )
        conversations_state[i].skip_next = False

    # TODO: refacto, load/init components and .then() add text
    return (
        # 2 conversations_state
        conversations_state
        # 2 chatbots
        + [x.to_gradio_chatbot() for x in conversations_state]
        # text
        + [""]
        # stepper_block
        + [gr.update(value=stepper_html("Discussion avec les modèles", 2, 4))]
        # mode_screen
        + [gr.update(visible=False)]
        # chat_area
        + [gr.update(visible=True)]
        # send_btn
        + [gr.update(interactive=False)]
        # retry_btn
        + [gr.update(visible=True)]
        # conclude_btn
        + [gr.update(visible=True, interactive=True)]
    )


def bot_response_multi(
    state0,
    state1,
    temperature,
    top_p,
    max_new_tokens,
    request: gr.Request,
):
    logger.info(f"bot_response_multi (anony). ip: {get_ip(request)}")

    if state0 is None or state0.skip_next:
        # This generate call is skipped due to invalid inputs
        yield (
            state0,
            state1,
            state0.to_gradio_chatbot(),
            state1.to_gradio_chatbot(),
        )
        return

    conversations_state = [state0, state1]
    gen = []
    for i in range(num_sides):
        gen.append(
            bot_response(
                conversations_state[i],
                temperature,
                top_p,
                max_new_tokens,
                request,
                apply_rate_limit=False,
                use_recommended_config=True,
            )
        )

    is_stream_batch = []
    for i in range(num_sides):
        is_stream_batch.append(
            conversations_state[i].model_name
            in [
                "gemini-pro",
                "gemini-pro-dev-api",
                "gemini-1.0-pro-vision",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemma-1.1-2b-it",
                "gemma-1.1-7b-it",
            ]
        )
    chatbots = [None] * num_sides
    iters = 0
    while True:
        stop = True
        iters += 1
        for i in range(num_sides):
            try:
                # yield gemini fewer times as its chunk size is larger
                # otherwise, gemini will stream too fast
                if not is_stream_batch[i] or (iters % 30 == 1 or iters < 3):
                    ret = next(gen[i])
                    conversations_state[i], chatbots[i] = ret[0], ret[1]
                stop = False
            except StopIteration:
                pass
        yield conversations_state + chatbots
        if stop:
            break


def check_for_tos_cookie(request: gr.Request):
    global tos_accepted
    if request:
        cookies_kv = request.headers["cookie"].split(";")
        for cookie_kv in cookies_kv:
            cookie_key, cookie_value = cookie_kv.split("=")
            if cookie_key == "languia_tos_accepted":
                if cookie_value == "1":
                    tos_accepted = True
                    return tos_accepted

    return tos_accepted


def clear_history(
    state0,
    state1,
    chatbot0,
    chatbot1,
    # model_selector0,
    # model_selector1,
    textbox,
    request: gr.Request,
):
    logger.info(f"clear_history (anony). ip: {get_ip(request)}")
    #     + chatbots
    # + model_selectors
    # + [textbox]
    # + [chat_area]
    # + [vote_area]
    # + [supervote_area]
    # + [mode_screen],
    return [
        None,
        None,
        None,
        None,
        # "",
        # "",
        "",
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
    ]


# build_arena_demo?
def build_arena(models):
    # conversations_state = [ConversationState() for _ in range(num_sides)]
    conversations_state = [gr.State() for _ in range(num_sides)]
    # model_selectors = [None] * num_sides
    # TODO: allow_flagging?
    chatbots = [None] * num_sides

    # TODO: check cookies on load!
    # tos_cookie = check_for_tos_cookie(request)
    # if not tos_cookie:

    with gr.Column(elem_classes="fr-container") as start_screen:
        # TODO: titre en bleu
        gr.Markdown(
            """
# Bienvenue dans l'arène LANGU:IA
###### Notre mission

Donner accès à différents modèles de langage (LLMs) conversationnels

###### Les règles de l'arène

Posez une question. Deux modèles vous répondent en temps réel.
Choisissez le modèle que vous préférez.
Découvrez l'identité des modèles et apprenez-en plus sur leurs caractéristiques.

###### Nos objectifs

**Diversité des langues** : Exprimez vous librement : vous parlez breton, occitan, basque, corse, créole ? Posez vos questions dans les dialectes, langues, argots ou registres que vous souhaitez !

**Identification des biais** : Posez des questions sur des domaines ou des tâches que vous maîtrisez. Constatez-vous certains partis-pris des modèles ?
        """
        )
        # TODO: DSFRize
        accept_tos_checkbox = gr.Checkbox(
            label="Conditions générales d'utilisation",
            show_label=True,
            elem_classes="",
        )
        start_arena_btn = gr.Button(
            value="C'est parti",
            scale=0,
            # TODO: à centrer
            elem_classes="fr-btn",
            interactive=False,
        )

    with gr.Row() as stepper_row:
        stepper_block = gr.HTML(
            stepper_html("Choix du mode de conversation", 1, 4),
            elem_id="stepper_html",
            visible=False,
        )

    with gr.Column(visible=False, elem_id="mode-screen") as mode_screen:
        mode_html = gr.HTML(
            """
        <div class="fr-notice fr-notice--info">
            <div class="fr-container">
                    <div class="fr-notice__body">
                                <p class="fr-notice__title">Discutez d'un sujet que vous connaissez ou qui vous intéresse puis évaluez les réponses des modèles</p>
                    </div>
            </div>
        </div>"""
        )
        gr.Markdown("#### Comment voulez-vous commencer la conversation ?")
        gr.Markdown("_(Sélectionnez un des deux modes)_")
        with gr.Row():
            with gr.Column():
                free_mode_btn = FrButton(
                    custom_html="<h3>Mode libre</h3><p>Ecrivez directement aux modèles, discutez du sujet que vous voulez</p>",
                    elem_id="free-mode",
                    icon="assets/artwork/pictograms/misc/conclusion.svg",
                )
            with gr.Column():
                guided_mode_btn = FrButton(
                    elem_id="guided-mode",
                    custom_html="<h3>Mode inspiré</h3><p>Vous n'avez pas d'idée ? Découvrez une série de thèmes inspirants</p>",
                    icon="assets/artwork/pictograms/misc/innovation.svg",
                )

        with gr.Column(
            visible=False, elem_id="guided-area", elem_classes=""
        ) as guided_area:
            gr.Markdown("##### Sélectionnez un thème que vous aimeriez explorer :")
            with gr.Row():
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
            with gr.Row():
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
            # guided_prompt = gr.Radio(
            #     choices=["Chtimi ?", "Québécois ?"], elem_classes="", visible=False
            # )

    with gr.Group(elem_id="chat-area", visible=False) as chat_area:
        with gr.Row():
            for i in range(num_sides):
                label = "Model A" if i == 0 else "Model B"
                with gr.Column():
                    # {likeable}
                    # placeholder
                    #         placeholder
                    # a placeholder message to display in the chatbot when it is empty. Centered vertically and horizontally in the Chatbot. Supports Markdown and HTML.
                    chatbots[i] = gr.Chatbot(
                        # container: bool = True par défaut,
                        # min_width=
                        # height=
                        # Doesn't seem to work, is it because it always has at least our message?
                        # Note: supports HTML, use it!
                        placeholder="**En chargement**",
                        # No difference
                        # bubble_full_width=False,
                        layout="panel",  # or "bubble"
                        likeable=True,
                        # TODO: move label
                        label=label,
                        elem_classes="chatbot",
                        # Could we show it? Useful...
                        show_copy_button=False,
                    )

                    # model_selectors[i] = gr.Markdown(
                    #     anony_names[i], elem_id="model_selector_md"
                    # )

    with gr.Column(elem_id="send-area", visible=False) as send_area:
        with gr.Row():
            # TODO: redevelop FrInput from Textbox and not SimpleTextbox
            textbox = FrInput(
                show_label=False,
                placeholder="Ecrivez votre premier message à l'arène ici",
                scale=3,
                # TODO:
                # autofocus=True
            )
            send_btn = gr.Button(value="Envoyer", scale=1, elem_classes="fr-btn")
            # FIXME: visible=false not working?
            retry_btn = gr.Button(
                icon="assets/icons/system/refresh-line.svg",
                value="",
                elem_classes="fr-btn",
                visible=False,
            )
        with gr.Row():
            # FIXME: visible=false not working?
            conclude_btn = gr.Button(
                value="Terminer et donner mon avis",
                scale=1,
                elem_classes="fr-btn",
                visible=False,
                interactive=False,
            )

    with gr.Column(visible=False) as vote_area:
        gr.Markdown(value="## Quel modèle avez-vous préféré ?")
        with gr.Row():
            which_model_radio = gr.Radio(show_label=False,
                choices=[
                    ("Modèle A", "leftvote"),
                    ("Modèle B", "rightvote"),
                    ("Aucun des deux", "bothbad"),
                ]
            )
            # leftvote_btn = gr.Button(value="👈  A est mieux")
            # rightvote_btn = gr.Button(value="👉  B est mieux")
            # # tie_btn = gr.Button(value="🤝  Les deux se valent")
            # bothbad_btn = gr.Button(value="👎  Aucun des deux")

    # TODO: render=false?
    with gr.Column(visible=False) as supervote_area:

        # TODO: render=false?
        # TODO: move to another file
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
            )
            pertinence_checkbox = gr.CheckboxGroup(
                [
                    "Incohérentes par rapport au contexte",
                    "Factuellement incorrectes",
                    "Imprécises",
                ],
                label="pertinence",
                info="Pertinence des réponses",
            )
            comprehension_checkbox = gr.CheckboxGroup(
                [
                    "Faible qualité de syntaxe",
                    "Pauvreté du vocabulaire",
                    "Mauvaise utilisation des expressions",
                ],
                label="comprehension",
                info="Compréhension et expression",
            )
            originalite_checkbox = gr.CheckboxGroup(
                ["Réponses banales", "Réponses superficielles"],
                label="originalite",
                info="Créativité et originalité",
            )

        supervote_checkboxes = [
            ressenti_checkbox,
            pertinence_checkbox,
            comprehension_checkbox,
            originalite_checkbox,
        ]

        comments_text = FrInput(
            label="Détails supplémentaires",
            # TODO:
            # info=,
            # autofocus=True,
            placeholder="Ajoutez plus de précisions ici",
        )
        final_send_btn = gr.Button(
            elem_classes="fr-btn", value="Envoyer mes préférences"
        )

        with gr.Row():
            # dsfr: These 2 should just be normal links...
            opinion_btn = gr.Button(value="Donner mon avis sur l'arène")

            # clear_btn = gr.Button(value="Recommencer sans voter")

            # dsfr: These 2 should just be normal links...
            leaderboard_btn = gr.Button(value="Liste des modèles")

    results_area = gr.HTML(visible=False)
    # with gr.Row(visible=False) as results_area:

    # for i in range(num_sides):
    #     with gr.Column():
    #         gr.HTML("Modèle A : "+str(conversations_state[0].model_name))
    #         gr.HTML("Modèle B : "+str(conversations_state[1].model_name))

    # gr.Markdown(
    #     get_model_description_md(models), elem_id="model_description_markdown"
    # )

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

    def show_component():
        return gr.update(visible=True)

    def enable_component():
        return gr.update(interactive=True)

    # Register listeners
    def register_listeners():
        # Step 0

        @accept_tos_checkbox.change(
            inputs=[accept_tos_checkbox],
            outputs=start_arena_btn,
            # doesn't work
            # scroll_to_output=True,
        )
        def accept_tos_to_enter_arena(accept_tos_checkbox):
            # Enable if checked
            return gr.update(interactive=accept_tos_checkbox)

        @start_arena_btn.click(
            inputs=[accept_tos_checkbox],
            outputs=[start_screen, stepper_block, mode_screen],
        )
        def check_tos(accept_tos_checkbox, request: gr.Request):
            global tos_accepted
            tos_accepted = accept_tos_checkbox
            if tos_accepted:
                print("ToS accepted!")
                return (
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=True),
                )
            else:
                print("ToS not accepted!")
                return (gr.skip(), gr.skip(), gr.skip())

        # TODO: fix js output
        # start_arena_btn.click(
        #     accept_tos, inputs=[], outputs=[start_screen, mode_screen], js=accept_tos_js
        # )
        # Step 1

        @free_mode_btn.click(
            inputs=[],
            # js?
            outputs=[guided_mode_btn, free_mode_btn, send_area, guided_area],
        )
        def free_mode():
            print("chose free mode!")
            return [
                gr.update(elem_classes=""),
                gr.update(elem_classes="selected"),
                gr.update(visible=True),
                gr.update(visible=False),
            ]

        @guided_mode_btn.click(
            inputs=[],
            outputs=[free_mode_btn, guided_mode_btn, send_area, guided_area],
            # TODO: scroll_to_output?
        )
        def guided_mode():
            print(guided_mode_btn.elem_classes)
            if "selected" in guided_mode_btn.elem_classes:
                return [gr.skip() * 4]
            else:
                print("chose guided mode!")
                return [
                    gr.update(elem_classes=""),
                    gr.update(elem_classes="selected"),
                    gr.update(visible=False),
                    gr.update(visible=True),
                ]

        # Step 1.1

        # TODO: refacto into RadioTile
        # FIXME: selected logic...
        def set_guided_prompt(event: gr.EventData):
            chosen_guide = event.target.value
            if chosen_guide == "maniere":
                preprompt = "Tu es Victor Hugo. Explique moi synthétiquement ce qu'est un LLM dans ton style d'écriture."
            elif chosen_guide == "registre":
                preprompt = "Parle argot wsh"
            elif chosen_guide == "creativite":
                preprompt = "Raconte-moi ta meilleure blague."
            elif chosen_guide == "pedagogie":
                preprompt = "Explique moi simplement ce qu'est la température d'un LLM"
            elif chosen_guide == "regional":
                preprompt = "Quoque ch'est qu'te berdoules ? Réponds en Chtimi."
            elif chosen_guide == "variete":
                preprompt = """Que veut dire "se sécher les dents" en Québécois ?"""
            else:
                print(chosen_guide)
                logger.error("Error, chosen guided prompt not listed")

            return [gr.update(visible=True), gr.update(value=preprompt)]

        gr.on(
            triggers=[
                maniere.click,
                registre.click,
                regional.click,
                variete.click,
                pedagogie.click,
                creativite_btn.click,
            ],
            fn=set_guided_prompt,
            inputs=[],
            outputs=[send_area, textbox],
        )

        # @guided_prompt.change(inputs=guided_prompt, outputs=[send_area, textbox])
        # def craft_guided_prompt(topic_choice):
        #     if str(topic_choice) == "Québécois ?":
        #         return [
        #             gr.update(visible=True),
        #             gr.update(value="Tu comprends-tu, quand je parle ?"),
        #         ]
        #     else:
        #         return [
        #             gr.update(visible=True),
        #             gr.update(value="Quoque ch'est qu'te berdoules ?"),
        #         ]

        # TODO: refacto so that it clears any object / trashes the state except ToS

        # Step 2

        @textbox.change(inputs=textbox, outputs=send_btn)
        def change_send_btn_state(textbox):
            if textbox == "":
                return gr.update(interactive=False)
            else:
                return gr.update(interactive=True)

        gr.on(
            triggers=[textbox.submit, send_btn.click],
            fn=add_text,
            inputs=conversations_state + [textbox],
            # inputs=conversations_state + model_selectors + [textbox],
            outputs=conversations_state
            + chatbots
            + [textbox]
            + [stepper_block]
            + [mode_screen]
            + [chat_area]
            + [send_btn]
            + [retry_btn]
            + [conclude_btn],
        ).then(
            bot_response_multi,
            conversations_state + [temperature, top_p, max_output_tokens],
            conversations_state + chatbots,
        ).then(
            enable_component, [], [conclude_btn]
        )

        def intermediate_like(state0, state1, event: gr.LikeData, request: gr.Request):
            # TODO: add model name?
            details = {"message": event.value["value"]}

            vote_type = "intermediate_"
            if event.liked:
                vote_type += "like_"
            else:
                vote_type += "dislike_"
            if event.target == chatbots[0]:
                vote_type += "left"
            elif event.target == chatbots[1]:
                vote_type += "right"
            else:
                logger.error("Like event for unknown chat")
            vote_last_response(
                [state0, state1],
                vote_type,
                details,
                request,
            )

        chatbots[0].like(intermediate_like, conversations_state, [])
        chatbots[1].like(intermediate_like, conversations_state, [])

        @conclude_btn.click(
            inputs=[],
            outputs=[stepper_block, chat_area, send_area, vote_area],
            # TODO: scroll_to_output?
        )
        def show_vote_area():
            # return {
            #     conclude_area: gr.update(visible=False),
            #     chat_area: gr.update(visible=False),
            #     send_area: gr.update(visible=False),
            #     vote_area: gr.update(visible=True),
            # }
            # [conclude_area, chat_area, send_area, vote_area]
            return [
                gr.update(value=stepper_html("Évaluation des modèles", 3, 4)),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True),
            ]

        @which_model_radio.change(
            inputs=[which_model_radio],
            outputs=[supervote_area, positive_supervote, negative_supervote],
        )
        def build_supervote_area(vote_radio):
            if vote_radio == "bothbad":
                return (
                    gr.update(visible=True),
                    gr.update(visible=False),
                    gr.update(visible=True),
                )
            else:
                print(vote_radio)
                return (
                    gr.update(visible=True),
                    gr.update(visible=True),
                    gr.update(visible=False),
                )

        # Step 3
        @final_send_btn.click(
            inputs=(
                [conversations_state[0]]
                + [conversations_state[1]]
                + [which_model_radio]
                + (supervote_checkboxes)
                + [comments_text]
            ),
            outputs=[
                stepper_block,
                vote_area,
                supervote_area,
                results_area,
            ],
        )
        def vote_preferences(
            state0,
            state1,
            which_model_radio,
            ressenti_checkbox,
            pertinence_checkbox,
            comprehension_checkbox,
            originalite_checkbox,
            comments_text,
            request: gr.Request,
        ):
            # conversations_state = [state0, state1]

            details = {
                "chosen_model": which_model_radio,
                "ressenti": ressenti_checkbox,
                "pertinence": pertinence_checkbox,
                "comprehension": comprehension_checkbox,
                "originalite": originalite_checkbox,
                "comments": comments_text,
            }
            if which_model_radio in ["bothbad", "leftvote", "rightvote"]:
                logger.info("Voting " + which_model_radio)

                vote_last_response(
                    [state0, state1],
                    which_model_radio,
                    details,
                    request,
                )
            else:
                logger.error(
                    'Model selection was neither "bothbad", "leftvote" or "rightvote", got: '
                    + str(which_model_radio)
                )

            return [
                gr.update(value=stepper_html("Révélation des modèles", 4, 4)),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(
                    visible=True,
                    value=build_reveal_html(
                        state0.model_name, state1.model_name, which_model_radio
                    ),
                ),
            ]
            # return vote

        # On reset go to mode selection mode_screen
        gr.on(
            triggers=[retry_btn.click],
            # triggers=[clear_btn.click, retry_btn.click],
            fn=clear_history,
            inputs=conversations_state + chatbots + [textbox],
            # inputs=conversations_state + chatbots + model_selectors + [textbox],
            # List of objects to clear
            outputs=conversations_state + chatbots
            # + model_selectors
            + [textbox] + [chat_area] + [vote_area] + [supervote_area] + [mode_screen],
        )

    register_listeners()

    return conversations_state
    # return conversations_state + model_selectors
