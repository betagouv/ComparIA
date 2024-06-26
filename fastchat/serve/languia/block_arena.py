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
    State,
    bot_response,
    get_conv_log_filename,
    get_ip,
    get_model_description_md,
)
from fastchat.serve.remote_logger import get_remote_logger
from fastchat.utils import (
    build_logger,
    moderation_filter,
)

logger = build_logger("gradio_web_server_multi", "gradio_web_server_multi.log")

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


def show_vote_area():
    # If I want this form, I need to use @render to refacto and have these already declared in that fn context by here
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

    states = (None,) * num_sides
    # What does it do???
    selector_updates = (
        gr.Markdown(visible=True),
        gr.Markdown(visible=True),
    )

    return states + selector_updates


def vote_last_response(states, vote_type, model_selectors, request: gr.Request):
    with open(get_conv_log_filename(), "a") as fout:
        data = {
            "tstamp": round(time.time(), 4),
            "type": vote_type,
            "models": [x for x in model_selectors],
            "states": [x.dict() for x in states],
            "ip": get_ip(request),
        }
        fout.write(json.dumps(data) + "\n")

    get_remote_logger().log(data)

    names = (
        "### Model A: " + states[0].model_name,
        "### Model B: " + states[1].model_name,
    )
    yield names + ("",)
    #  + [gr.update(visible=True)]


def leftvote_last_response(
    state0, state1, model_selector0, model_selector1, request: gr.Request
):
    logger.info(f"leftvote (anony). ip: {get_ip(request)}")
    for x in vote_last_response(
        [state0, state1], "leftvote", [model_selector0, model_selector1], request
    ):
        yield x


def rightvote_last_response(
    state0, state1, model_selector0, model_selector1, request: gr.Request
):
    logger.info(f"rightvote (anony). ip: {get_ip(request)}")
    for x in vote_last_response(
        [state0, state1], "rightvote", [model_selector0, model_selector1], request
    ):
        yield x


def tievote_last_response(
    state0, state1, model_selector0, model_selector1, request: gr.Request
):
    logger.info(f"tievote (anony). ip: {get_ip(request)}")
    for x in vote_last_response(
        [state0, state1], "tievote", [model_selector0, model_selector1], request
    ):
        yield x


def bothbad_vote_last_response(
    state0, state1, model_selector0, model_selector1, request: gr.Request
):
    logger.info(f"bothbad_vote (anony). ip: {get_ip(request)}")
    for x in vote_last_response(
        [state0, state1], "bothbad_vote", [model_selector0, model_selector1], request
    ):
        yield x


def get_sample_weight(model, outage_models, sampling_weights, sampling_boost_models):
    if model in outage_models:
        return 0
    weight = sampling_weights.get(model, 0)
    if model in sampling_boost_models:
        weight *= 5
    return weight


def get_battle_pair(
    models, battle_targets, outage_models, sampling_weights, sampling_boost_models
):
    if len(models) == 1:
        return models[0], models[0]

    model_weights = []
    for model in models:
        weight = get_sample_weight(
            model, outage_models, sampling_weights, sampling_boost_models
        )
        model_weights.append(weight)
    total_weight = np.sum(model_weights)
    model_weights = model_weights / total_weight
    chosen_idx = np.random.choice(len(models), p=model_weights)
    chosen_model = models[chosen_idx]
    # for p, w in zip(models, model_weights):
    #     print(p, w)

    rival_models = []
    rival_weights = []
    for model in models:
        if model == chosen_model:
            continue
        weight = get_sample_weight(
            model, outage_models, sampling_weights, sampling_boost_models
        )
        if (
            weight != 0
            and chosen_model in battle_targets
            and model in battle_targets[chosen_model]
        ):
            # boost to 50% chance
            weight = total_weight / len(battle_targets[chosen_model])
        rival_models.append(model)
        rival_weights.append(weight)
    # for p, w in zip(rival_models, rival_weights):
    #     print(p, w)
    rival_weights = rival_weights / np.sum(rival_weights)
    rival_idx = np.random.choice(len(rival_models), p=rival_weights)
    rival_model = rival_models[rival_idx]

    swap = np.random.randint(2)
    if swap == 0:
        return chosen_model, rival_model
    else:
        return rival_model, chosen_model


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
    states = [state0, state1]
    model_selectors = [model_selector0, model_selector1]

    # Init states if necessary
    if states[0] is None:
        assert states[1] is None

        model_left, model_right = get_battle_pair(
            models,
            BATTLE_TARGETS,
            OUTAGE_MODELS,
            SAMPLING_WEIGHTS,
            SAMPLING_BOOST_MODELS,
        )
        states = [
            State(model_left),
            State(model_right),
        ]

    # FIXME: when submitting empty text
    # if len(text) <= 0:
    #     for i in range(num_sides):
    #         states[i].skip_next = True
    #     return (
    #         # 2 states
    #         states
    #         # 2 chatbots
    #         + [x.to_gradio_chatbot() for x in states]
    #         # text
    #         + [""]
    #         + [visible_row]
    #         # Slow warning
    #         + [""]
    #     )

    model_list = [states[i].model_name for i in range(num_sides)]
    # turn on moderation in battle mode
    all_conv_text_left = states[0].conv.get_prompt()
    all_conv_text_right = states[0].conv.get_prompt()
    all_conv_text = (
        all_conv_text_left[-1000:] + all_conv_text_right[-1000:] + "\nuser: " + text
    )
    flagged = moderation_filter(all_conv_text, model_list, do_moderation=False)
    if flagged:
        logger.info(f"violate moderation (anony). ip: {ip}. text: {text}")
        # overwrite the original text
        text = MODERATION_MSG

    conv = states[0].conv
    if (len(conv.messages) - conv.offset) // 2 >= CONVERSATION_TURN_LIMIT:
        logger.info(f"conversation turn limit. ip: {get_ip(request)}. text: {text}")
        for i in range(num_sides):
            states[i].skip_next = True
            # TODO: refacto
        return (
            # 2 states
            states
            # 2 chatbots
            + [x.to_gradio_chatbot() for x in states]
            # text
            + [CONVERSATION_LIMIT_MSG]
            + [gr.update(visible=True)]
        )

    text = text[:BLIND_MODE_INPUT_CHAR_LEN_LIMIT]  # Hard cut-off
    # TODO: what do?
    for i in range(num_sides):
        # post_processed_text = _prepare_text_with_image(states[i], text, csam_flag=False)
        post_processed_text = text
        states[i].conv.append_message(states[i].conv.roles[0], post_processed_text)
        states[i].conv.append_message(states[i].conv.roles[1], None)
        states[i].skip_next = False

    return (
        # 2 states
        states
        # 2 chatbots
        + [x.to_gradio_chatbot() for x in states]
        # text
        + [""]
        # gr.group visible
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

    states = [state0, state1]
    gen = []
    for i in range(num_sides):
        gen.append(
            bot_response(
                states[i],
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
            states[i].model_name
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
                    states[i], chatbots[i] = ret[0], ret[1]
                stop = False
            except StopIteration:
                pass
        yield states + chatbots
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


# TODO: à move
def accept_tos(request: gr.Request):
    global tos_accepted
    tos_accepted = True

    print("ToS accepted!")
    return [
        # start_screen:
        gr.update(visible=False),
        # mode_screen:
        gr.update(visible=True),
    ]


def choose_mode(choosen_mode_button):
    # global languia_state
    # languia_state.tos_accepted = True
    print("chose mode!")
    return [
        gr.Row(visible=False),
        gr.Row(visible=True),
    ]


accept_tos_js = """
function () {
  document.cookie="languia_tos_accepted=1"
}
"""


def build_side_by_side_ui_anony(models):
    states = [gr.State() for _ in range(num_sides)]
    model_selectors = [None] * num_sides
    # TODO: allow_flagging?
    chatbots = [None] * num_sides

    # TODO: check cookies on load!
    # tos_cookie = check_for_tos_cookie(request)
    # if not tos_cookie:
    with gr.Row() as start_screen:
        accept_tos_btn = gr.Button(value="🔄  Accept ToS", interactive=True)

    with gr.Row(visible=False) as mode_screen:
        # render: no?
        free_mode_btn = gr.Button(
            value="🎲 Mode libre",
            interactive=True,
        )
        guided_mode_btn = gr.Button(
            value="🎲 Mode inspiré",
            interactive=True,
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

    with gr.Row(visible=False) as send_area:
        # TODO: use @gr.render instead?
        textbox = gr.Textbox(
            show_label=False,
            placeholder="Ecrivez votre premier message à l'arène ici",
            elem_id="input_box",
            elem_classes="fr-input",
        )
        send_btn = gr.Button(value="Envoyer", scale=0, elem_classes="fr-btn")

    # TODO: visible à update quand "terminer l'exp"
    with gr.Row(visible=False) as conclude_area:
        conclude_btn = gr.Button(value="Terminer et donner mon avis")
        clear_btn = gr.Button(value="Recommencer sans voter")
    # TODO: visible à update quand "terminer l'exp"

    with gr.Row(visible=False) as vote_area:
        gr.Markdown(value="## Quel modèle avez-vous préféré ?")
        leftvote_btn = gr.Button(value="👈  A est mieux")
        rightvote_btn = gr.Button(value="👉  B est mieux")
        tie_btn = gr.Button(value="🤝  Les deux se valent")
        bothbad_btn = gr.Button(value="👎  Aucun des deux")

    with gr.Row(visible=False) as supervote_area:
        gr.Markdown(
            value="### Pourquoi ce choix de modèle ?\nSélectionnez vos préférences (facultatif)"
        )
        gr.Markdown(value="Ressenti")
        with gr.Group():
            # TODO: refacto
            lisible_btn = gr.Button(value="Lisible")
            impressionne_btn = gr.Button(value="Impressionné")
            facile_a_comprendre_btn = gr.Button(value="Facile à comprendre")
        final_text = gr.TextArea(placeholder="Ajoutez plus de détails ici")
        final_send_btn = gr.Button(value="Envoyer mes préférences")
        with gr.Row():
            # These 2 should just be normal links...
            opinion_btn = gr.Button(value="Donner mon avis sur l'arène")
            leaderboard_btn = gr.Button(value="Classement de l'arène")

            # TODO: re-render clear btn instead
            clear_btn = gr.Button(value="Nouvelle conversation")

    # TODO: refacto so that it clears any object
    def clear_history(request: gr.Request):
        logger.info(f"clear_history (anony). ip: {get_ip(request)}")
        # FIXME: cleanup better
        return (
            # states
            # + chatbots
            # + model_selectors
            # + [textbox]
            # + [vote_area]
            # + [supervote_area]
            # + [mode_screen],
            {
                states: [None, None],
                chatbots: [None, None],
                model_selectors: anony_names,
                textbox: [""],
                vote_area: gr.update(visible=False),
                supervote_area: gr.update(visible=False),
                mode_screen: gr.update(visible=True),
            },
        )

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

    # TODO: export listeners to another file
    # Register listeners

    accept_tos_btn.click(
        accept_tos, inputs=[], outputs=[start_screen, mode_screen]
    )
    # TODO: fix js output
    # accept_tos_btn.click(
    #     accept_tos, inputs=[], outputs=[start_screen, mode_screen], js=accept_tos_js
    # )
    guided_mode_btn.click(
        choose_mode,
        inputs=[guided_mode_btn],
        outputs=[mode_screen, send_area],
    )
    free_mode_btn.click(
        choose_mode,
        inputs=[free_mode_btn],
        outputs=[mode_screen, send_area],
    )

    textbox.submit(
        add_text,
        states + model_selectors + [textbox],
        states + chatbots + [textbox] + [chat_area],
    ).then(
        bot_response_multi,
        states + [temperature, top_p, max_output_tokens],
        states + chatbots,
    ).then(show_component, [], [conclude_area])

    send_btn.click(
        add_text,
        states + model_selectors + [textbox],
        states + chatbots + [textbox] + [chat_area],
    ).then(
        bot_response_multi,
        states + [temperature, top_p, max_output_tokens],
        states + chatbots,
    ).then(show_component, [], [conclude_area])

    conclude_btn.click(
        show_vote_area, [], [conclude_area, chat_area, send_area, vote_area]
    )

    leftvote_btn.click(
        leftvote_last_response,
        states + model_selectors,
        model_selectors,
        #  + [supervote_area],
    ).then(show_component, [], [supervote_area])
    rightvote_btn.click(
        rightvote_last_response,
        states + model_selectors,
        model_selectors,
        #  + [supervote_area],
    ).then(show_component, [], [supervote_area])
    tie_btn.click(
        tievote_last_response,
        states + model_selectors,
        model_selectors,
        #  + [supervote_area],
    ).then(show_component, [], [supervote_area])
    bothbad_btn.click(
        bothbad_vote_last_response,
        states + model_selectors,
        model_selectors + [supervote_area],
    ).then(show_component, [], [supervote_area])
    # FIXME:
    clear_btn.click(
        clear_history,
        [],
        # List of objects to clear
        states
        + chatbots
        + model_selectors
        + [textbox]
        + [vote_area]
        + [supervote_area]
        + [mode_screen],
    )
    # TODO: rationalize, do a common state?
    return states + model_selectors
