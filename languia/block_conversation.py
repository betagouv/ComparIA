"""
The gradio utilities for chatting with a single model.
"""

import datetime
import json
import os
import time
import uuid

import gradio as gr
import requests

from fastchat.constants import (
    WORKER_API_TIMEOUT,
    ErrorCode,
    MODERATION_MSG,
    CONVERSATION_LIMIT_MSG,
    RATE_LIMIT_MSG,
    SERVER_ERROR_MSG,
    INPUT_CHAR_LEN_LIMIT,
    CONVERSATION_TURN_LIMIT,
    SESSION_EXPIRATION_TIME,
)

# from fastchat.model.model_adapter import (
#     get_conversation_template,
# )
from languia.api_provider import get_api_provider_stream_iter


from languia.utils import get_ip, is_limit_reached
from languia import config

import logging

logger = logging.getLogger("languia")

def set_conv_state(state, model_name=""):
        # self.messages = get_conversation_template(model_name)
    state.messages = []
    state.output_tokens = None

    # TODO: get it from api if generated
    state.conv_id = uuid.uuid4().hex

    # TODO: add template info? and test it
    state.template_name = "zero_shot"
    state.template = []
    state.model_name = model_name
    return state

def update_last_message(messages, text):
    if len(messages) < 1:
        return [gr.ChatMessage(role="assistant", content=text)]
    # We append a new assistant message if last one was from user
    if messages[-1].role == "user":
        messages.append(gr.ChatMessage(role="assistant", content=text))
    else:
        messages[-1].content = text
    return messages


def bot_response(
    state,
    request: gr.Request,
    temperature=0.7,
    top_p=1.0,
    max_new_tokens=1024,
    apply_rate_limit=True,
    use_recommended_config=True,
):
    # start_tstamp = time.time()
    # temperature = float(temperature)
    # top_p = float(top_p)
    # max_new_tokens = int(max_new_tokens)

    if apply_rate_limit:
        ip = get_ip(request)
        ret = is_limit_reached(state.model_name, ip)
        if ret is not None and ret["is_limit_reached"]:
            error_msg = RATE_LIMIT_MSG + "\n\n" + ret["reason"]
            logger.warn(f"rate limit reached. error_msg: {ret['reason']}")
            # state.conv.update_last_message(error_msg)
            # yield (state, state.to_gradio_chatbot()) + (no_change_btn,) * 5
            raise RuntimeError(error_msg)

    messages, model_name = state.messages, state.model_name
    model_api_dict = (
        config.api_endpoint_info[model_name]
        if model_name in config.api_endpoint_info
        else None
    )

    if model_api_dict is None:
        logger.critical("No model for model name: " + model_name)
    else:
        if use_recommended_config:
            recommended_config = model_api_dict.get("recommended_config", None)
            if recommended_config is not None:
                temperature = recommended_config.get("temperature", float(temperature))
                top_p = recommended_config.get("top_p", float(top_p))
                max_new_tokens = recommended_config.get(
                    "max_new_tokens", int(max_new_tokens)
                )
        try:
            stream_iter = get_api_provider_stream_iter(
                messages,
                model_name,
                model_api_dict,
                temperature,
                top_p,
                max_new_tokens,
                state,
                request,
            )
        except Exception as e:
            logger.error(
                f"Error in get_api_provider_stream_iter. error: {e}",
                extra={request: request},
            )

    html_code = "<br /><br /><em>En attente de la réponse…</em>"

    update_last_message(messages, html_code)
    yield (state)

    data = {"text": ""}

    # FIXME: does not detect/raise if 500 error
    for i, data in enumerate(stream_iter):
        if "output_tokens" in data:
            # logger.debug("reported output tokens:" + str(data["output_tokens"]))
            # Sum of all previous interactions
            if not state.output_tokens:
                state.output_tokens = 0
            state.output_tokens += data["output_tokens"]

        if data["error_code"] == 0:
            # Artificially slow faster Google Vertex API
            # if not (model_api_dict["api_type"] == "vertex" and i % 15 != 0):
            output = data["text"].strip()
            messages = update_last_message(messages, output + html_code)
            yield (state)
        else:
            raise RuntimeError(data["text"] + f"\n\n(error_code: {data['error_code']})")
    # FIXME: weird way of checking if the stream never answered, openai api doesn't seem to raise anything

    output = data["text"].strip()
    if output == "":
        raise RuntimeError(f"No answer from API for model {model_name}")

    messages = update_last_message(messages, output)

    yield (state)
    # TODO: handle them great, or reboot arena saving initial prompt
    # except requests.exceptions.RequestException as e:
    #     conv.update_last_message(
    #         f"{SERVER_ERROR_MSG}\n\n"
    #         f"(error_code: {ErrorCode.GRADIO_REQUEST_ERROR}, {e})"
    #     )
    #     return
    # except Exception as e:
    #     conv.update_last_message(
    #         f"{SERVER_ERROR_MSG}\n\n"
    #         f"(error_code: {ErrorCode.GRADIO_STREAM_UNKNOWN_ERROR}, {e})"
    #     )
    #     return


# finish_tstamp = time.time()
