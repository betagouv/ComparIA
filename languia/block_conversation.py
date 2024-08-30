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
from fastchat.conversation import Conversation, SeparatorStyle

# from fastchat.model.model_adapter import (
#     get_conversation_template,
# )
from languia.api_provider import get_api_provider_stream_iter


from languia.utils import get_ip, is_limit_reached
from languia import config

import logging as logger


# from gradio.components.base import Component
class ConversationState(gr.State):
    def __init__(self, model_name="", is_vision=False):
        # TODO: use std OpenAI format instead
        # self.conv = get_conversation_template(model_name)
        self.messages = []

        # TODO: get it from api
        self.conv_id = uuid.uuid4().hex

        self.model_name = model_name

    def dict(self):
        base = self.conv.dict()
        base.update(
            {
                "conv_id": self.conv_id,
                "model_name": self.model_name,
            }
        )
        return base


def bot_response(
    state,
    temperature,
    top_p,
    max_new_tokens,
    request: gr.Request,
    apply_rate_limit=True,
    use_recommended_config=False,
):
    ip = get_ip(request)
    logger.info(f"bot_response. ip: {ip}")
    start_tstamp = time.time()
    temperature = float(temperature)
    top_p = float(top_p)
    max_new_tokens = int(max_new_tokens)

    if apply_rate_limit:
        ret = is_limit_reached(state.model_name, ip)
        if ret is not None and ret["is_limit_reached"]:
            error_msg = RATE_LIMIT_MSG + "\n\n" + ret["reason"]
            logger.warn(f"rate limit reached. ip: {ip}. error_msg: {ret['reason']}")
            # state.conv.update_last_message(error_msg)
            # yield (state, state.to_gradio_chatbot()) + (no_change_btn,) * 5
            raise RuntimeError(error_msg)

    conv, model_name = state.conv, state.model_name
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
                temperature = recommended_config.get("temperature", temperature)
                top_p = recommended_config.get("top_p", top_p)
                max_new_tokens = recommended_config.get(
                    "max_new_tokens", max_new_tokens
                )
        try:
            stream_iter = get_api_provider_stream_iter(
                conv,
                model_name,
                model_api_dict,
                temperature,
                top_p,
                max_new_tokens,
                state,
            )
        except Exception as e:
            logger.error(f"Error in get_api_provider_stream_iter. error: {e}")

    html_code = "<br /><br /><em>En attente de la réponse…</em>"

    # conv.update_last_message("▌")
    messages[-1].content = html_code
    yield (state)

    data = {"text": ""}
    # FIXME: does not detect/raise if 500 error
    for i, data in enumerate(stream_iter):
        if data["error_code"] == 0:
            output = data["text"].strip()
            # conv.update_last_message(output + "▌")
            messages[-1].content = output + html_code
            yield (state)
        else:
            raise RuntimeError(data["text"] + f"\n\n(error_code: {data['error_code']})")
    # FIXME: weird way of checking if the stream never answered, openai api doesn't seem to raise anything

    output = data["text"].strip()
    if output == "":
        raise RuntimeError(f"No answer from API for model {model_name}")
    messages[-1].content = output
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
    # # logger.info(f"{output}")

    # filename = get_conv_log_filename(
    #     # is_vision=state.is_vision, has_csam_image=state.has_csam_image
    # )
    # logger.info(f"Saving to: {filename}")

    # with open(filename, "a") as fout:
    #     data = {
    #         "tstamp": round(finish_tstamp, 4),
    #         "type": "chat",
    #         "model": model_name,
    #         "gen_params": {
    #             "temperature": temperature,
    #             "top_p": top_p,
    #             "max_new_tokens": max_new_tokens,
    #         },
    #         "start": round(start_tstamp, 4),
    #         "finish": round(finish_tstamp, 4),
    #         "state": state.dict(),
    #         "ip": get_ip(request),
    #     }
    #     fout.write(json.dumps(data) + "\n")
