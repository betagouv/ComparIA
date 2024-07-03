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

from fastchat.serve.languia.components import stepper_html
from fastchat.serve.languia.actions import (
    vote_preferences,
    #     # send_preferences,
    #     bothbad_vote_last_response,
    #     # tievote_last_response,
    #     rightvote_last_response,
    #     leftvote_last_response,
)

from fastchat.utils import (
    build_logger,
    moderation_filter,
)

from fastchat.serve.languia.utils import get_battle_pair

from gradio_frbutton import FrButton
from gradio_frinput import FrInput

logger = build_logger("gradio_web_server_multi", "gradio_web_server_multi.log")

# TODO: move to constants.py
num_sides = 2
enable_moderation = False

anony_names = ["", ""]
models = []

tos_accepted = False


def set_global_vars_anony(enable_moderation_):
    global enable_moderation
    enable_moderation = enable_moderation_


def show_component():
    return gr.update(visible=True)


def enable_component():
    return gr.update(interactive=True)


# TODO: à refacto
def show_vote_area():
    # If I want this form, I need to use .render() to refacto and have these already declared in that fn context by here
    # return {
    #     conclude_area: gr.update(visible=False),
    #     chat_area: gr.update(visible=False),
    #     send_area: gr.update(visible=False),
    #     vote_area: gr.update(visible=True),
    # }
    # [conclude_area, chat_area, send_area, vote_area]
    return [
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
    ]


def load_demo_arena(models_, url_params):
    global models
    models = models_

    conversations_state = (None,) * num_sides
    # What does it do???
    selector_updates = (
        gr.Markdown(visible=True),
        gr.Markdown(visible=True),
    )

    return conversations_state + selector_updates


def add_text(
    state0: gr.State,
    state1: gr.State,
    model_selector0: gr.Markdown,
    model_selector1: gr.Markdown,
    text: gr.Text,
    request: gr.Request,
):
    ip = get_ip(request)
    logger.info(f"add_text (anony). ip: {ip}. len: {len(text)}")
    conversations_state = [state0, state1]
    model_selectors = [model_selector0, model_selector1]

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
            ConversationState(model_left),
            ConversationState(model_right),
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
        # conclude_area
        + [gr.update(visible=True)]
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
    model_selector0,
    model_selector1,
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
        "",
        "",
        "",
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
    ]


# build_arena_demo?
def build_arena(models):
    conversations_state = [gr.State() for _ in range(num_sides)]
    model_selectors = [None] * num_sides
    # TODO: allow_flagging?
    chatbots = [None] * num_sides

    # TODO: check cookies on load!
    # tos_cookie = check_for_tos_cookie(request)
    # if not tos_cookie:

    with gr.Column(elem_classes="fr-container") as start_screen:
        # TODO: titre en bleu
        gr.Markdown("""
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
        """)
        # TODO: DSFRize
        accept_tos_checkbox = gr.Checkbox(
            label="Conditions générales d'utilisation",
            show_label=True,
            elem_classes="",
        )
        start_arena_btn = gr.Button(
            value="C'est parti",
            interactive=True,
            scale=0,
            # TODO: à centrer
            elem_classes="fr-btn",
        )

    with gr.Row() as stepper_row:
        stepper_block = gr.HTML(
            stepper_html("Choix du mode de conversation", 1, 4),
            elem_id="stepper_html",
            visible=False,
        )

    with gr.Column(visible=False) as mode_screen:
        mode_html = gr.HTML("""
        <div class="fr-notice fr-notice--info">
            <div class="fr-container">
                    <div class="fr-notice__body">
                                <p class="fr-notice__title">Discutez d'un sujet que vous connaissez ou qui vous intéresse puis évaluez les réponses des modèles</p>
                    </div>
            </div>
        </div>""")
        gr.Markdown("#### Comment voulez-vous commencer la conversation ?")
        gr.Markdown("_(Sélectionnez un des deux modes)_")
        with gr.Row():
            with gr.Column():
                free_mode_btn = FrButton(
                    custom_html="<h3>Mode libre</h3><p>Ecrivez directement aux modèles, discutez du sujet que vous voulez</p>",
                    elem_id="free-mode",
                    icon="assets/artwork/pictograms/document/contract.svg",
                )
            with gr.Column():
                guided_mode_btn = FrButton(
                    custom_html="<h3>Mode inspiré</h3><p>Vous n'avez pas d'idée ? Découvrez une série de thèmes inspirants</p>",
                    icon="assets/artwork/pictograms/leisure/community.svg",
                )

        with gr.Row(visible=False, elem_classes="") as guided_area:
            maniere = FrButton(
                custom_html='''<span class="fr-badge">Style</span><p>Ecrire à la manière d'un romancier ou d'une romancière</p>'''
            )
            registre = FrButton(
                custom_html='''<span class="fr-badge">Style</span><p>Ecrire à la manière d'un romancier ou d'une romancière</p>'''
            )
            creativite = FrButton(
                custom_html='''<span class="fr-badge">Style</span><p>Ecrire à la manière d'un romancier ou d'une romancière</p>'''
            )
            pedagogie = FrButton(
                custom_html='''<span class="fr-badge">Style</span><p>Ecrire à la manière d'un romancier ou d'une romancière</p>'''
            )
            regional = FrButton(
                custom_html='''<span class="fr-badge">Style</span><p>Ecrire à la manière d'un romancier ou d'une romancière</p>'''
            )
            variete = FrButton(
                custom_html='''<span class="fr-badge">Style</span><p>Ecrire à la manière d'un romancier ou d'une romancière</p>'''
            )
            guided_prompt = gr.Radio(
                choices=["Chtimi ?", "Québécois ?"], elem_classes=""
            )

    with gr.Group(elem_id="chat-area", visible=False) as chat_area:
        with gr.Row():
            for i in range(num_sides):
                label = "Model A" if i == 0 else "Model B"
                with gr.Column():
                    chatbots[i] = gr.Chatbot(
                        label=label,
                        elem_id="chatbot",
                        show_copy_button=True,
                    )

        with gr.Row():
            for i in range(num_sides):
                with gr.Column():
                    model_selectors[i] = gr.Markdown(
                        anony_names[i], elem_id="model_selector_md"
                    )

    with gr.Row(elem_id="send-area", visible=False) as send_area:
        # with gr.Row():
        textbox = FrInput(
            show_label=False,
            placeholder="Ecrivez votre premier message à l'arène ici",
            elem_classes="fr-input",
            scale=3,
        )
        send_btn = gr.Button(value="Envoyer", scale=1, elem_classes="fr-btn")
        # FIXME: visible=false not working?
        retry_btn = gr.Button(
            value="Recommencer", elem_classes="fr-btn", scale=0, visible=False
        )

    with gr.Row(visible=False) as conclude_area:
        conclude_btn = gr.Button(
            value="Terminer et donner mon avis",
            scale=1,
            elem_classes="fr-btn",
            interactive=True,
            # interactive=False
        )

    with gr.Column(visible=False) as vote_area:
        gr.Markdown(value="## Quel modèle avez-vous préféré ?")
        with gr.Row():
            which_model_radio = gr.Radio(
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

    with gr.Column(visible=False) as supervote_area:
        gr.Markdown(
            value="### Pourquoi ce choix de modèle ?\nSélectionnez vos préférences (facultatif)"
        )
        with gr.Row():
            # TODO: refacto
            ressenti_checkbox = gr.CheckboxGroup(
                ["Lisible", "Impressionné·e", "Facile à comprendre"],
                label="ressenti",
                info="Quel a été votre ressenti ?",
            )
            # ressenti_checkbox = gr.CheckboxGroup(["Lisible", "Impressionné·e", "Facile à comprendre"], label="ressenti", info="Quel a été votre ressenti ?")
            # ressenti_checkbox = gr.CheckboxGroup(["Lisible", "Impressionné·e", "Facile à comprendre"], label="ressenti", info="Quel a été votre ressenti ?")
        comments_text = gr.TextArea(placeholder="Ajoutez plus de détails ici")
        final_send_btn = gr.Button(value="Envoyer mes préférences")

        with gr.Row():
            # dsfr: These 2 should just be normal links...
            leaderboard_btn = gr.Button(value="Classement de l'arène")

            # dsfr: These 2 should just be normal links...
            opinion_btn = gr.Button(value="Donner mon avis sur l'arène")
            clear_btn = gr.Button(value="Recommencer sans voter")

    # with gr.Row() as results_area:
    #     gr.Markdown(get_model_description_md(models), elem_id="model_description_markdown")

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

    # Register listeners
    def register_listeners():
        # Step 0
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
        )
        def guided_mode():
            print(guided_mode_btn.elem_classes)
            if "selected" in guided_mode_btn.elem_classes:
                return [gr.skip()*4]
            else:
                print("chose guided mode!")
                return [
                    gr.update(elem_classes=""),
                    gr.update(elem_classes="selected"),
                    gr.update(visible=False),
                    gr.update(visible=True),
                ]
        # Step 1.1
        @guided_prompt.change(inputs=guided_prompt, outputs=[send_area, textbox])
        def craft_guided_prompt(topic_choice):
            if str(topic_choice) == "Québécois ?":
                return [
                    gr.update(visible=True),
                    gr.update(value="Tu comprends-tu, quand je parle ?"),
                ]
            else:
                return [
                    gr.update(visible=True),
                    gr.update(value="Quoque ch'est qu'te berdoules ?"),
                ]

            # TODO: refacto so that it clears any object / trashes the state except ToS

        def change_send_btn_state(textbox):
            if textbox != "":
                return gr.update(interactive=True)
            else:
                return gr.update(interactive=False)

        # Step 2
        textbox.change(change_send_btn_state, textbox, send_btn)

        gr.on(
            triggers=[textbox.submit, send_btn.click],
            fn=add_text,
            inputs=conversations_state + model_selectors + [textbox],
            outputs=conversations_state
            + chatbots
            + [textbox]
            + [stepper_block]
            + [mode_screen]
            + [chat_area]
            + [send_btn]
            + [retry_btn]
            + [conclude_area],
        ).then(
            bot_response_multi,
            conversations_state + [temperature, top_p, max_output_tokens],
            conversations_state + chatbots,
        ).then(enable_component, [], [conclude_btn])

        conclude_btn.click(
            show_vote_area, [], [conclude_area, chat_area, send_area, vote_area]
        )

        which_model_radio.change(show_component, [], [supervote_area])
        
        # Step 3
        final_send_btn.click(
            vote_preferences,
            conversations_state
            + [which_model_radio]
            + [ressenti_checkbox]
            + [comments_text],
            [],
        )
        # On reset go to mode selection mode_screen
        gr.on(
            triggers=[clear_btn.click, retry_btn.click],
            fn=clear_history,
            inputs=conversations_state + chatbots + model_selectors + [textbox],
            # List of objects to clear
            outputs=conversations_state
            + chatbots
            + model_selectors
            + [textbox]
            + [chat_area]
            + [vote_area]
            + [supervote_area]
            + [mode_screen],
        )

    register_listeners()

    return conversations_state + model_selectors
