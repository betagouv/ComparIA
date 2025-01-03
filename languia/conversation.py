"""
The gradio utilities for chatting with a single model.
"""

import gradio as gr

import random
from languia.api_provider import get_api_provider_stream_iter

import time
from custom_components.customchatbot.backend.gradio_customchatbot.customchatbot import (
    ChatMessage,
)

from languia.utils import (
    ContextTooLongError,
    EmptyResponseError,
)
from languia import config

import logging

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
            logger.warning(f"'model_id' is not defined in endpoint: {endpoint}.")
        elif "api_id" not in endpoint:
            logger.warning(f"'api_id' is not defined in endpoint: {endpoint}.")
        
        else:
            if (endpoint.get("model_id")) == state.model_name:
                model_api_endpoints.append(endpoint)

    if model_api_endpoints == []:
        logger.critical("No endpoint for model name: " + str(state.model_name))
    else:
        if state.endpoint is None:
            state.endpoint = random.choice(model_api_endpoints)
            endpoint_name = state.endpoint["api_id"]
            logger.info(f"picked_endpoint: {endpoint_name} for {state.model_name}")
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
        try:
            start_tstamp = time.time()
            print("start: " + str(start_tstamp))

            stream_iter = get_api_provider_stream_iter(
                state.messages,
                endpoint,
                temperature,
                max_new_tokens,
                request,
            )
        except Exception as e:
            logger.error(
                f"Error in get_api_provider_stream_iter. error: {e}",
                extra={request: request},
            )

    output_tokens = None

    start = time.time()
    import sys

    def trace_function(frame, event, arg):
        if time.time() - start_tstamp > 10:
            raise Exception('Timed out!') # Use whatever exception you consider appropriate.
        return trace_function
    

    for i, data in enumerate(stream_iter):
        sys.settrace(trace_function)
        try:
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
        finally:
            sys.settrace(None) # Remove the time constraint and continue normally.

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

import uuid
def set_conv_state(state, model_name, endpoint):
    # self.messages = get_conversation_template(model_name)
    state.messages = []
    state.output_tokens = None

    # TODO: get it from api if generated
    state.conv_id = uuid.uuid4().hex

    # TODO: add template info? and test it
    state.template_name = "zero_shot"
    state.template = []
    state.model_name = model_name
    state.endpoint = endpoint
    return state
