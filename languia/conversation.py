import gradio as gr

from languia.litellm import litellm_stream_iter

import time
from custom_components.customchatbot.backend.gradio_customchatbot.customchatbot import (
    ChatMessage,
)

from languia.utils import (
    EmptyResponseError,
    get_endpoint,
    messages_to_dict_list,
)
from languia import config

import logging

from uuid import uuid4


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
        self.output_tokens = None
        self.conv_id = str(uuid4()).replace("-", "")
        self.model_name = model_name
        self.endpoint = get_endpoint(model_name)


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


# import sys


def bot_response(
    position,
    state,
    request: gr.Request,
    temperature=0.7,
    # top_p=1.0,
    max_new_tokens=4096,
    apply_rate_limit=True,
    use_recommended_config=True,
):
    # temperature = float(temperature)
    # top_p = float(top_p)
    # max_new_tokens = int(max_new_tokens)

    # TODO: apply rate limit by ip

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
    if use_recommended_config:
        recommended_config = endpoint.get("recommended_config", None)
        if recommended_config is not None:
            temperature = recommended_config.get("temperature", float(temperature))
            # top_p = recommended_config.get("top_p", float(top_p))
            max_new_tokens = recommended_config.get(
                "max_new_tokens", int(max_new_tokens)
            )
            include_reasoning = recommended_config.get("include_reasoning", False)

    start_tstamp = time.time()
    # print("start: " + str(start_tstamp))

    messages_dict = messages_to_dict_list(state.messages)
    litellm_model_name = (
        endpoint.get("api_type", "openai") + "/" + endpoint["model_name"]
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
    if output_tokens:
        if state.output_tokens is None:
            state.output_tokens = output_tokens

    state.messages = update_last_message(
        messages=state.messages,
        text=output,
        position=position,
        output_tokens=output_tokens,
        duration=duration,
        reasoning=reasoning,
    )

    yield (state)
