import gradio as gr

from languia.litellm import litellm_stream_iter
from litellm.litellm_core_utils.token_counter import token_counter

import time
from languia.custom_components.customchatbot import (
    ChatMessage,
)

from languia.utils import EmptyResponseError, messages_to_dict_list, get_api_key
from languia import config

import logging

from uuid import uuid4

from languia.config import models


class Conversation:
    def __init__(
        self,
        messages=[],
        model_name=None,
    ):

        system_prompt = config.get_model_system_prompt(model_name)
        if system_prompt:
            self.messages = [
                ChatMessage(role="system", content=system_prompt)
            ] + messages
        else:
            self.messages = messages
        self.conv_id = str(uuid4()).replace("-", "")
        self.model_name = model_name
        self.endpoint = models.get(model_name, {}).get("endpoint", {})


logger = logging.getLogger("languia")


def update_last_message(
    messages,
    text,
    position,
    output_tokens=None,
    generation_id=None,
    duration=0,
    reasoning=None,
):
    # Create metadata dictionary with optional fields
    metadata = {
        "bot": position,
        **({"output_tokens": output_tokens} if output_tokens else {}),
        **({"generation_id": generation_id} if generation_id else {}),
        **({"duration": duration} if duration != 0 else {}),
    }

    # Create new message if needed
    if not messages or messages[-1].role == "user":
        return messages + [
            ChatMessage(
                role="assistant", content=text, metadata=metadata, reasoning=reasoning
            )
        ]

    # Update existing message
    last_message = messages[-1]
    last_message.content = text
    last_message.metadata = {**last_message.metadata, **metadata}
    if reasoning is not None:
        last_message.reasoning = reasoning

    return messages


def bot_response(
    position,
    state,
    request: gr.Request,
    temperature=0.7,
    # top_p=1.0,
    max_new_tokens=4096,
):
    # temperature = float(temperature)
    # top_p = float(top_p)
    # max_new_tokens = int(max_new_tokens)

    if not state.endpoint:
        logger.critical(
            "No endpoint for model name: " + str(state.model_name),
            extra={"request": request},
        )
        raise Exception("No endpoint for model name: " + str(state.model_name))

    endpoint = state.endpoint

    endpoint_name = endpoint.get("api_id", state.model_name)
    logger.info(
        f"using endpoint {endpoint_name} for {state.model_name}",
        extra={"request": request},
    )
    include_reasoning = False

    start_tstamp = time.time()
    # print("start: " + str(start_tstamp))

    messages_dict = messages_to_dict_list(state.messages)
    litellm_model_name = (
        endpoint.get("api_type", "openai")
        + "/"
        + endpoint.get("api_model_id", state.model_name)
    )

    api_key = get_api_key(endpoint)

    stream_iter = litellm_stream_iter(
        model_name=litellm_model_name,
        messages=messages_dict,
        temperature=temperature,
        api_key=api_key,
        api_base=endpoint.get("api_base", None),
        api_version=endpoint.get("api_version", None),
        # stream=model_api_dict.get("stream", True),
        # top_p=top_p,
        max_new_tokens=max_new_tokens,
        request=request,
        vertex_ai_location=endpoint.get("vertex_ai_location", None),
        include_reasoning=include_reasoning,
    )

    output_tokens = None
    generation_id = None

    for i, data in enumerate(stream_iter):

        if "output_tokens" in data:
            output_tokens = data["output_tokens"]
        if "generation_id" in data:
            generation_id = data["generation_id"]

        output = data.get("text")
        reasoning = data.get("reasoning")
        if output or reasoning:
            output.strip()
            state.messages = update_last_message(
                messages=state.messages,
                text=output,
                position=position,
                output_tokens=output_tokens,
                generation_id=generation_id,
                reasoning=reasoning,
            )
            yield (state)

    if generation_id:
        logger.info(
            f"generation_id: {generation_id} for {litellm_model_name}",
            extra={"request": request},
        )

    stop_tstamp = time.time()
    # print("stop: " + str(stop_tstamp))
    duration = stop_tstamp - start_tstamp
    logger.debug(
        f"duration for {generation_id}: {str(duration)}", extra={"request": request}
    )

    output = data.get("text")
    reasoning = data.get("reasoning")
    if (not output or output == "") and (not reasoning or reasoning == ""):
        logger.error(
            f"reponse_vide: {state.model_name}, data: " + str(data),
            exc_info=True,
            extra={"request": request},
        )
        # logger.error(data)
        raise EmptyResponseError(
            f"No answer from API {endpoint_name} for model {state.model_name}"
        )
    if not output_tokens:
        output_tokens = token_counter(text=[reasoning, output], model=state.model_name)
    state.messages = update_last_message(
        messages=state.messages,
        text=output,
        position=position,
        output_tokens=output_tokens,
        duration=duration,
        reasoning=reasoning,
    )

    yield (state)
