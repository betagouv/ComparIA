"""
Utilities to communicate with different APIs
"""

import os
import logging

import sentry_sdk

from gradio import ChatMessage

from languia.utils import ContextTooLongError, EmptyResponseError

import openai


def openai_stream(
    messages,
    model_api_dict,
    temperature,
    max_new_tokens,
    request=None,
):
    logger = logging.getLogger("languia")
    messages_dict = []
    for message in messages:
        if isinstance(message, ChatMessage):
            messages_dict.append({"role": message.role, "content": message.content})
        else:
            raise TypeError(f"Expected ChatMessage object, got {type(message)}")
    if model_api_dict["api_type"] == "openai":
        api_key = model_api_dict["api_key"]
    elif model_api_dict["api_type"] == "vertex":

        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            logger.warn("No Google creds detected!")

        import google.auth
        import google.auth.transport.requests

        # Programmatically get an access token
        # creds, project = google.auth.default()
        creds, project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        api_key = creds
    else:
        raise NotImplementedError()

    api_base = model_api_dict["api_base"]
    model_name = model_api_dict["model_name"]

    client = openai.OpenAI(
        base_url=api_base,
        api_key=api_key,
        # max_retries=
        #         timeout=WORKER_API_TIMEOUT,
        # timeout=5,
        #     timeout=httpx.Timeout(5, read=5, write=5, connect=2
        # )
    )
    
    response = client.chat.completions.create(
        model=model_name,
        messages=messages_dict,
        temperature=temperature,
        max_tokens=max_new_tokens,
        stream=True,
        stream_options={"include_usage": True},
        # Not available like this
        # top_p=top_p,
    )
    # print(response.response.__dict__)
    # response = response.parse()

    text = ""
    logger = logging.getLogger("languia")

    data = dict()
    buffer = ""
    # buffer_output_tokens = 0
    chunks_log = []

    for chunk in response:
        if hasattr(chunk, "usage") and hasattr(chunk.usage, "completion_tokens"):
            data["output_tokens"] = chunk.usage.completion_tokens
        if hasattr(chunk, "choices") and len(chunk.choices) > 0:
            if hasattr(chunk.choices[0], "finish_reason"):
                if chunk.choices[0].finish_reason == "stop":
                    data["text"] = text
                    break
                elif chunk.choices[0].finish_reason == "length":
                    # cannot raise ContextTooLong because sometimes the model stops only because of current answer's (output) length limit, e.g. HuggingFace free API w/ Phi
                    # raise ContextTooLongError
                    logger.warning("context_too_long: " + str(chunk))
                    chunks_log.append(chunk)

                    if os.getenv("SENTRY_DSN"):
                        sentry_sdk.capture_message(str(chunks_log))
                    break
            if hasattr(chunk.choices[0], "delta") and hasattr(
                chunk.choices[0].delta, "content"
            ):
                content = chunk.choices[0].delta.content
            if not content:
                content = ""
                logger.debug("no_content_in_chunk: " + str(chunk))
                # TODO: check if it's the first yield and keep all empty and not-first yields
                # if os.getenv("SENTRY_DSN"):
                #     sentry_sdk.capture_message(str(chunks_log))
                continue

            # Special handling for certain models
            if model_name == "meta/llama3-405b-instruct-maas":
                content = content.replace("\\n", "\n").lstrip("assistant")
            elif model_name == "google/gemini-1.5-pro-001":
                content = content.replace("<br />", "")

            text += content
            buffer += content

            data["text"] = text

        if len(buffer.split()) >= 30:
            # if len(buffer.split()) >= 30 or len(text.split()) < 30:
            # if "\n" in buffer or "." in buffer:

            # Reset word count after yielding
            # data["output_tokens"] = buffer_output_tokens
            buffer = ""
            # buffer_output_tokens = 0

            yield data
    # else:
        # raise Empty
    yield data
