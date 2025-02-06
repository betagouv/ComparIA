"""
The gradio utilities for chatting with a single model.
"""

import gradio as gr

import random
from languia.litellm import litellm_stream_iter

import time
from custom_components.customchatbot.backend.gradio_customchatbot.customchatbot import (
    ChatMessage,
)

from languia.utils import ContextTooLongError, EmptyResponseError
from languia import config

import logging

from uuid import uuid4

logger = logging.getLogger("languia")


def update_last_message(messages, text, position, output_tokens=None):

    metadata = {"bot": position}
    if output_tokens:
        metadata["output_tokens"] = output_tokens

    if not messages:
        return [ChatMessage(role="assistant", content=text, metadata=metadata)]

    last_message = messages[-1]
    if last_message.role == "user":
        messages.append(ChatMessage(role="assistant", content=text, metadata=metadata))
    else:
        last_message.content = text
        last_message.metadata.update(metadata)

    return messages


# import sys


def bot_response(
    position,
    state,
    request: gr.Request,
    temperature=0.7,
    # top_p=1.0,
    max_new_tokens=2048,
    apply_rate_limit=True,
    use_recommended_config=True,
):
    # temperature = float(temperature)
    # top_p = float(top_p)
    # max_new_tokens = int(max_new_tokens)

    # if apply_rate_limit:
    #     ip = get_ip(request)
    #     ret = is_limit_reached(state.model_name, ip)
    #     if ret is not None and ret["is_limit_reached"]:
    #         error_msg = RATE_LIMIT_MSG + "\n\n" + ret["reason"]
    #         logger.warn(f"rate limit reached. error_msg: {ret['reason']}")

    model_api_endpoints = []

    for endpoint in config.api_endpoint_info:
        if "model_id" not in endpoint:
            logger.warning(f"'model_id' is not defined in endpoint: {endpoint}.", extra={request: request})
        elif "api_id" not in endpoint:
            logger.warning(f"'api_id' is not defined in endpoint: {endpoint}.", extra={request: request})

        else:
            if (endpoint.get("model_id")) == state.model_name:
                model_api_endpoints.append(endpoint)

    if model_api_endpoints == []:
        logger.critical("No endpoint for model name: " + str(state.model_name), extra={request: request})
        raise Exception("No endpoint for model name: " + str(state.model_name))

    if state.endpoint is None:
        state.endpoint = random.choice(model_api_endpoints)
        endpoint_name = state.endpoint["api_id"]
        logger.info(f"picked_endpoint: {endpoint_name} for {state.model_name}", extra={request: request})

    endpoint = state.endpoint
    endpoint_name = endpoint["api_id"]
    if use_recommended_config:
        recommended_config = endpoint.get("recommended_config", None)
        if recommended_config is not None:
            temperature = recommended_config.get("temperature", float(temperature))
            # top_p = recommended_config.get("top_p", float(top_p))
            max_new_tokens = recommended_config.get(
                "max_new_tokens", int(max_new_tokens)
            )

    start_tstamp = time.time()
    print("start: " + str(start_tstamp))
    
    messages_dict = []

    for message in state.messages:
        try:
            messages_dict.append({"role": message.role, "content": message.content})
        except:
            raise TypeError(f"Expected ChatMessage object, got {type(message)}")

    litellm_model_name = (
        endpoint.get("api_type", "openai")
        + "/"
        + endpoint["model_name"]
    )
    stream_iter = litellm_stream_iter(
        model_name=litellm_model_name,
        messages=messages_dict,
        temperature=temperature,
        api_key=endpoint.get("api_key", "F4K3-4P1-K3Y"),
        api_base=endpoint.get("api_base", None),
        api_version=endpoint.get("api_version", None),
        # stream=model_api_dict.get("stream", True),
        # top_p=top_p,
        max_new_tokens=max_new_tokens,
        request=request,
        vertex_ai_location=endpoint.get("vertex_ai_location", None),
    )

    output_tokens = None

    for i, data in enumerate(stream_iter):
        if "output_tokens" in data:
            output_tokens = data["output_tokens"]

        output = data.get("text")
        if output:
            output.strip()
            state.messages = update_last_message(
                messages=state.messages,
                text=output,
                position=position,
                output_tokens=output_tokens,
            )
            yield (state)

    stop_tstamp = time.time()
    print("stop: " + str(stop_tstamp))

    output = data.get("text")
    if not output or output == "":
        logger.error(
            f"reponse_vide: {state.model_name}, data: " + str(data),
            exc_info=True,
            extra={request: request},
        )
        # logger.error(data)
        raise EmptyResponseError(
            f"No answer from API {endpoint_name} for model {state.model_name}"
        )
    if output_tokens:
        if state.output_tokens is None:
            state.output_tokens = output_tokens

    state.messages = update_last_message(
        messages=state.messages,
        text=output,
        position=position,
        output_tokens=output_tokens,
    )

    yield (state)


def set_conv_state(state, model_name, endpoint):
    # self.messages = get_conversation_template(model_name)
    state.messages = []
    state.output_tokens = None

    # TODO: get it from api if generated
    state.conv_id = uuid4().hex

    # TODO: add template info? and test it
    state.template_name = "zero_shot"
    state.template = []
    state.model_name = model_name
    state.endpoint = endpoint
    return state
