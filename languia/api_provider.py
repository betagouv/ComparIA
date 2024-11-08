"""
Utilities to communicate with different APIs
"""

import os
import logging

import sentry_sdk

from gradio import ChatMessage

from languia.utils import ContextTooLongError, EmptyResponseError


def get_api_provider_stream_iter(
    messages,
    model_api_dict,
    temperature,
    max_new_tokens,
    request=None,
):
    messages_dict = []
    for message in messages:
        if isinstance(message, ChatMessage):
            messages_dict.append({"role": message.role, "content": message.content})
        else:
            raise TypeError(f"Expected ChatMessage object, got {type(message)}")
    if model_api_dict["api_type"] == "openai":
        stream_iter = openai_api_stream_iter(
            model_name=model_api_dict["model_name"],
            messages=messages_dict,
            temperature=temperature,
            max_new_tokens=max_new_tokens,
            api_base=model_api_dict["api_base"],
            api_key=model_api_dict["api_key"],
            request=request,
        )
    elif model_api_dict["api_type"] == "vertex":
        stream_iter = vertex_api_stream_iter(
            model_name=model_api_dict["model_name"],
            messages=messages_dict,
            temperature=temperature,
            # top_p=top_p,
            max_new_tokens=max_new_tokens,
            api_base=model_api_dict["api_base"],
            request=request,
        )
    else:
        raise NotImplementedError()

    return stream_iter


def process_response_stream(response, model_name=None, request=None):
    """
    Processes the stream of responses from the OpenAI API.
    """
    text = ""
    logger = logging.getLogger("languia")

    data = dict()
    # data["text"] = ""
    buffer = ""
    # buffer_output_tokens = 0
    chunks_log = []

    for chunk in response:
        if hasattr(chunk, "usage") and hasattr(chunk.usage, "completion_tokens"):
            # buffer_output_tokens = chunk.usage.completion_tokens
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
            else:
                content = ""
            if not content:
                content = ""
                logger.debug("no_content_in_chunk: " + str(chunk))
                chunks_log.append(chunk)

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
    # data["output_tokens"] = buffer_output_tokens
    else:
        # if os.getenv("SENTRY_DSN"):
            # sentry_sdk.capture_message(response.__dict__)
            # sentry_sdk.capture_message(response.response.__dict__)
        raise EmptyResponseError()
    yield data
    # except Exception as e:
    #     logger.error("erreur_chunk: " + str(chunk))
    #     raise e


def openai_api_stream_iter(
    model_name,
    messages,
    temperature,
    max_new_tokens,
    api_base=None,
    api_key=None,
    request=None,
):
    import openai

    api_key = api_key

    client = openai.OpenAI(
        base_url=api_base,
        api_key=api_key,
        #         timeout=WORKER_API_TIMEOUT,
        timeout=5,
        # max_retries=
    )

    #
    res = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_new_tokens,
        stream=True,
        stream_options={"include_usage": True},
        # Not available like this
        # top_p=top_p,
    )
    yield from process_response_stream(res, model_name=model_name, request=request)


def vertex_api_stream_iter(
    api_base, model_name, messages, temperature, max_new_tokens, request=None
):
    # import vertexai
    # from vertexai import generative_models
    # from vertexai.generative_models import (
    #     GenerationConfig,
    #     GenerativeModel,
    #     Image,
    # )
    # GOOGLE_APPLICATION_CREDENTIALS
    logger = logging.getLogger("languia")

    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        logger.warn("No Google creds detected!")

    import google.auth
    import google.auth.transport.requests
    import openai

    # Programmatically get an access token
    # creds, project = google.auth.default()
    creds, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    # Note: the credential lives for 1 hour by default (https://cloud.google.com/docs/authentication/token-types#at-lifetime); after expiration, it must be refreshed.

    # Pass the Vertex endpoint and authentication to the OpenAI SDK
    # PROJECT = project
    client = openai.OpenAI(base_url=api_base, api_key=creds.token)

    # print(client.models.list())
    # project_id = os.environ.get("GCP_PROJECT_ID", None)
    # location = os.environ.get("GCP_LOCATION", None)
    # vertexai.init(project=project_id, location=location)

    # gen_params = {
    #     "model": model_name,
    #     "prompt": messages,
    #     "temperature": temperature,
    #     "top_p": top_p,
    #     "max_new_tokens": max_new_tokens,
    # }
    # logging.info(f"==== request ====\n{gen_params}")

    # safety_settings = [
    #     generative_models.SafetySetting(
    #         category=generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT,
    #         threshold=generative_models.HarmBlockThreshold.BLOCK_NONE,
    #     ),
    #     generative_models.SafetySetting(
    #         category=generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
    #         threshold=generative_models.HarmBlockThreshold.BLOCK_NONE,
    #     ),
    #     generative_models.SafetySetting(
    #         category=generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
    #         threshold=generative_models.HarmBlockThreshold.BLOCK_NONE,
    #     ),
    #     generative_models.SafetySetting(
    #         category=generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
    #         threshold=generative_models.HarmBlockThreshold.BLOCK_NONE,
    #     ),
    # ]

    res = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
        max_tokens=max_new_tokens,
        stream=True,
        stream_options={"include_usage": True},
    )
    yield from process_response_stream(res, model_name=model_name, request=request)

    # generator = GenerativeModel(model_name).generate_content(
    #     messages,
    #     stream=True,
    #     generation_config=GenerationConfig(
    #         top_p=top_p, max_output_tokens=max_new_tokens, temperature=temperature
    #     ),
    #     safety_settings=safety_settings,
    # )

    # ret = ""
    # for chunk in generator:
    #     # NOTE(chris): This may be a vertex api error, below is HOTFIX: https://github.com/googleapis/python-aiplatform/issues/3129
    #     ret += chunk.candidates[0].content.parts[0]._raw_part.text
    #     # ret += chunk.text
    #     data = {
    #         "text": ret,
    #         "error_code": 0,
    #     }
    #     yield data


# Not used
# def model_worker_stream_iter(
#     conv,
#     model_name,
#     worker_addr,
#     prompt,
#     temperature,
#     repetition_penalty,
#     top_p,
#     max_new_tokens,
#     images,
# ):
#     # Make requests
#     gen_params = {
#         "model": model_name,
#         "prompt": prompt,
#         "temperature": temperature,
#         "repetition_penalty": repetition_penalty,
#         "top_p": top_p,
#         "max_new_tokens": max_new_tokens,
#         "stop": conv.stop_str,
#         "stop_token_ids": conv.stop_token_ids,
#         "echo": False,
#     }

#     logger.info(f"==== request ====\n{gen_params}")

#     if len(images) > 0:
#         gen_params["images"] = images

#     # Stream output
#     response = requests.post(
#         worker_addr + "/worker_generate_stream",
#         headers=config.headers,
#         json=gen_params,
#         stream=True,
#         timeout=WORKER_API_TIMEOUT,
#     )
#     for chunk in response.iter_lines(decode_unicode=False, delimiter=b"\0"):
#         if chunk:
#             data = json.loads(chunk.decode())
#             yield data
