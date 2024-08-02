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


from languia.utils import get_ip, get_conv_log_filename, is_limit_reached
from languia import config

import logging as logger

no_change_btn = gr.Button()
enable_btn = gr.Button(interactive=True, visible=True)
disable_btn = gr.Button(interactive=False)
invisible_btn = gr.Button(interactive=False, visible=False)

# from gradio.components.base import Component
class ConversationState(gr.State):
    def __init__(self, model_name="", is_vision=False):
        # TODO: use std OpenAI format instead
        # self.conv = get_conversation_template(model_name)
        self.conv = Conversation(
            name="zero_shot",
            system_message="",
            # system_message="A chat between a curious human and an artificial intelligence assistant. "
            # "The assistant gives helpful, detailed, and polite answers to the human's questions.",
            roles=("user", "assistant"),
            sep_style=SeparatorStyle.ADD_COLON_SINGLE,
            sep="\n### ",
            stop_str="###",
        ).copy()

        # TODO: get it from api
        self.conv_id = uuid.uuid4().hex

        self.model_name = model_name
        self.oai_thread_id = None
        # self.is_vision = is_vision

        # self.conv.history

    # def generate_response(history):
    #     history.append(ChatMessage(role="user", content="What is the weather in San Francisco right now?"))
    #     yield history
    #     time.sleep(0.25)
    #     history.append(ChatMessage(role="assistant",
    #                                   content="In order to find the current weather in San Francisco, I will need to use my weather tool.")
    #                                )
    #     yield history

    # TODO: get rid
    def to_gradio_chatbot(self):
        return self.conv.to_gradio_chatbot()

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

# TODO: remove, shouldn't happen anymore
    if state.skip_next:
        # This generate call is skipped due to invalid inputs
        state.skip_next = False
        yield (state, state.to_gradio_chatbot()) + (no_change_btn,) * 5
        return

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
        logger.critical("No model for model name: "+model_name)
    else:
        if use_recommended_config:
            recommended_config = model_api_dict.get("recommended_config", None)
            if recommended_config is not None:
                temperature = recommended_config.get("temperature", temperature)
                top_p = recommended_config.get("top_p", top_p)
                max_new_tokens = recommended_config.get(
                    "max_new_tokens", max_new_tokens
                )

        stream_iter = get_api_provider_stream_iter(
            conv,
            model_name,
            model_api_dict,
            temperature,
            top_p,
            max_new_tokens,
            state,
        )

    html_code = "<br /><br /><em>En attente de la réponse…</em>"

    # conv.update_last_message("▌")
    conv.update_last_message(html_code)
    yield (state, state.to_gradio_chatbot())

    data = {"text": ""}
    for i, data in enumerate(stream_iter):
        if data["error_code"] == 0:
            output = data["text"].strip()
            # conv.update_last_message(output + "▌")
            conv.update_last_message(output + html_code)
            yield (state, state.to_gradio_chatbot())
        else:
            raise RuntimeError(data["text"] + f"\n\n(error_code: {data['error_code']})")
            
    output = data["text"].strip()
    conv.update_last_message(output)
    yield (state, state.to_gradio_chatbot())
        # TODO: handle them great, or reboot arena saving initial prompt
    # except requests.exceptions.RequestException as e:
    #     conv.update_last_message(
    #         f"{SERVER_ERROR_MSG}\n\n"
    #         f"(error_code: {ErrorCode.GRADIO_REQUEST_ERROR}, {e})"
    #     )
    #     yield (state, state.to_gradio_chatbot()) + (
    #         disable_btn,
    #         disable_btn,
    #         disable_btn,
    #         enable_btn,
    #         enable_btn,
    #     )
    #     return
    # except Exception as e:
    #     conv.update_last_message(
    #         f"{SERVER_ERROR_MSG}\n\n"
    #         f"(error_code: {ErrorCode.GRADIO_STREAM_UNKNOWN_ERROR}, {e})"
    #     )
    #     yield (state, state.to_gradio_chatbot()) + (
    #         disable_btn,
    #         disable_btn,
    #         disable_btn,
    #         enable_btn,
    #         enable_btn,
    #     )
    #     return

    finish_tstamp = time.time()
    logger.info(f"{output}")

    filename = get_conv_log_filename(
        # is_vision=state.is_vision, has_csam_image=state.has_csam_image
    )
    logger.info(f"Saving to: {filename}")

    with open(filename, "a") as fout:
        data = {
            "tstamp": round(finish_tstamp, 4),
            "type": "chat",
            "model": model_name,
            "gen_params": {
                "temperature": temperature,
                "top_p": top_p,
                "max_new_tokens": max_new_tokens,
            },
            "start": round(start_tstamp, 4),
            "finish": round(finish_tstamp, 4),
            "state": state.dict(),
            "ip": get_ip(request),
        }
        fout.write(json.dumps(data) + "\n")
