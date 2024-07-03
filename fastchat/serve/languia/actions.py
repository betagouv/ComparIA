import gradio as gr

import time

import json

from fastchat.serve.languia.block_conversation import get_conv_log_filename, get_ip

from fastchat.serve.remote_logger import get_remote_logger

from fastchat.utils import (
    build_logger,
    # moderation_filter,
)

logger = build_logger("gradio_web_server_multi", "gradio_web_server_multi.log")


def vote_last_response(
    conversations_state,
    vote_type,
    _model_selectors,
    preferences: [],
    request: gr.Request,
):
    logger.info(f"{vote_type}_vote (anony). ip: {get_ip(request)}")
    preferences_str = json.dumps(preferences)
    logger.info(f"preferences: {preferences_str}")

    with open(get_conv_log_filename(), "a") as fout:
        data = {
            "tstamp": round(time.time(), 4),
            "type": vote_type,
            "models": [x.model_name for x in conversations_state],
            "conversations_state": [x.dict() for x in conversations_state],
            "ip": get_ip(request),
            "preferences": preferences,
        }
        logger.info(json.dumps(data))
        fout.write(json.dumps(data) + "\n")

    get_remote_logger().log(data)

    names = (
        "### Model A: " + conversations_state[0].model_name,
        "### Model B: " + conversations_state[1].model_name,
    )
    return data
    # yield names + ("",)


# TODO: refacto: why the loop?
# def leftvote_last_response(
#     state0, state1, model_selector0, model_selector1, request: gr.Request
# ):
#     for x in vote_last_response(
#         [state0, state1], "leftvote", [model_selector0, model_selector1], request
#     ):
#         yield x


# def rightvote_last_response(
#     state0, state1, model_selector0, model_selector1, request: gr.Request
# ):
#     for x in vote_last_response(
#         [state0, state1], "rightvote", [model_selector0, model_selector1], request
#     ):
#         yield x


# # def tievote_last_response(
# #     state0, state1, model_selector0, model_selector1, request: gr.Request
# # ):
# #     for x in vote_last_response(
# #         [state0, state1], "tievote", [model_selector0, model_selector1], request
# #     ):
# #         yield x


# def bothbad_vote_last_response(
#     state0, state1, model_selector0, model_selector1, request: gr.Request
# ):
#     for x in vote_last_response(
#         [state0, state1], "bothbad_vote", [model_selector0, model_selector1], request
#     ):
#         yield x


# def vote(conversations_state, vote_type, request: gr.Request):
#     models_names = [
#         conversations_state[0].model_name,
#         conversations_state[1].model_name,
#     ]

#     vote_last_response(
#         conversations_state[0],
#         conversations_state[1],
#         models_names[0],
#         models_names[1],
#         vote_type,
#         request,
#     )


def vote_preferences(
    state0,
    state1,
    which_model_radio,
    # FIXME: more checkboxes
    ressenti_checkbox,
    comments_text,
    request: gr.Request,
):
    conversations_state = [state0, state1]
    models_names = [
        conversations_state[0].model_name,
        conversations_state[1].model_name,
    ]
    preferences = {
        "chosen_model": which_model_radio,
        "ressenti": ressenti_checkbox,
        "comments": comments_text,
    }
    if which_model_radio in ["bothbad", "leftvote", "rightvote"]:
        logger.info("Voting " + which_model_radio)
        vote = vote_last_response(
            [state0, state1],
            which_model_radio,
            models_names,
            preferences,
            request,
        )
    else:
        logger.error(
            'Model selection was neither "bothbad", "leftvote" or "rightvote", got: '
            + str(which_model_radio)
        )

    return []
    # return vote


accept_tos_js = """
function () {
  document.cookie="languia_tos_accepted=1"
}
"""
