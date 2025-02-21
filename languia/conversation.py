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

class Conversation:
    def __init__(
        self,
        messages=[],
        output_tokens=None,
        model_name=None,
    ):

        system_prompt = config.get_model_system_prompt(model_name)
        if system_prompt:
            self.messages = [ChatMessage(role="system",content=system_prompt)] + messages
        else:
            self.messages = messages
        self.output_tokens = output_tokens
        self.conv_id = str(uuid4())
        self.model_name = model_name
        self.endpoint = pick_endpoint(model_name)


logger = logging.getLogger("languia")


def update_last_message(messages, text, position, output_tokens=None,generation_id=None,duration=0):

    metadata = {"bot": position}
    if output_tokens:
        metadata["output_tokens"] = output_tokens
    if generation_id:
        metadata["generation_id"] = generation_id
    if duration != 0:
        metadata["duration"] = duration

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
            logger.warning(f"'model_id' is not defined in endpoint: {endpoint}.", extra={"request": request})
        elif "api_id" not in endpoint:
            logger.warning(f"'api_id' is not defined in endpoint: {endpoint}.", extra={"request": request})

        else:
            if (endpoint.get("model_id")) == state.model_name:
                model_api_endpoints.append(endpoint)

    if model_api_endpoints == []:
        logger.critical("No endpoint for model name: " + str(state.model_name), extra={"request": request})
        raise Exception("No endpoint for model name: " + str(state.model_name))

    if state.endpoint is None:
        state.endpoint = random.choice(model_api_endpoints)
        endpoint_name = state.endpoint["api_id"]
        logger.info(f"picked_endpoint: {endpoint_name} for {state.model_name}", extra={"request": request})

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
    # print("start: " + str(start_tstamp))
    
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
    generation_id = None

    for i, data in enumerate(stream_iter):
        if "output_tokens" in data:
            output_tokens = data["output_tokens"]
        if "generation_id" in data:
            generation_id = data["generation_id"]

        output = data.get("text")
        if output:
            output.strip()
            state.messages = update_last_message(
                messages=state.messages,
                text=output,
                position=position,
                output_tokens=output_tokens,
                generation_id=generation_id
            )
            yield (state)

    if generation_id:
        logger.info(f"generation_id: {generation_id} for {litellm_model_name}", extra={"request": request})

    stop_tstamp = time.time()
    # print("stop: " + str(stop_tstamp))
    duration = stop_tstamp - start_tstamp
    logger.debug(f"duration for {generation_id}: {str(duration)}", extra={"request": request})

    output = data.get("text")
    if not output or output == "":
        logger.error(
            f"reponse_vide: {state.model_name}, data: " + str(data),
            exc_info=True,
            extra={"request": request},
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
        duration=duration,

    )

    yield (state)

