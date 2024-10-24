"""
The gradio utilities for chatting with a single model.
"""
import gradio as gr

from languia.api_provider import get_api_provider_stream_iter

import time

from languia.utils import (
    ContextTooLongError,
    EmptyResponseError,
)
from languia import config

import logging

logger = logging.getLogger("languia")


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
    max_new_tokens=2048,
    apply_rate_limit=True,
    use_recommended_config=True,
):
    start_tstamp = time.time()
    print("start:"+str(start_tstamp))
    # temperature = float(temperature)
    # top_p = float(top_p)
    # max_new_tokens = int(max_new_tokens)

    # if apply_rate_limit:
    #     ip = get_ip(request)
    #     ret = is_limit_reached(state.model_name, ip)
    #     if ret is not None and ret["is_limit_reached"]:
    #         error_msg = RATE_LIMIT_MSG + "\n\n" + ret["reason"]
    #         logger.warn(f"rate limit reached. error_msg: {ret['reason']}")
    #         # state.conv.update_last_message(error_msg)
    #         # yield (state, state.to_gradio_chatbot()) + (no_change_btn,) * 5
    #         raise RuntimeError(error_msg)

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
                model_api_dict,
                temperature,
                top_p,
                max_new_tokens,
                state,
                request,
            )
            # We could check if stream is already closed
        except Exception as e:
            logger.error(
                f"Error in get_api_provider_stream_iter. error: {e}",
                extra={request: request},
                exc_info=True,
            )

    html_code = "<br /><br /><em>En attente de la réponse…</em>"

    # update_last_message(messages, html_code)
    yield (state)

    for i, data in enumerate(stream_iter):
        if "output_tokens" in data:
            if not state.output_tokens:
                state.output_tokens = 0

            state.output_tokens += data["output_tokens"]

        output = data.get("text")
        if output:
            output.strip()
            messages = update_last_message(messages, output + html_code)
            yield (state)

    output = data.get("text")
    if not output or output == "":
        logger.error(
            f"reponse_vide: {model_name}, data: " + str(data),
            exc_info=True,
            extra={request: request},
        )
        # logger.error(data)
        # FIXME: normally already raised earlier
        raise EmptyResponseError(f"No answer from API for model {model_name}")

    messages = update_last_message(messages, output)

    finish_tstamp = time.time()
    print("finish:"+str(finish_tstamp))
    yield (state)

