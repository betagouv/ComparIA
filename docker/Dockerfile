# FROM nvidia/cuda:12.2.0-runtime-ubuntu20.04 AS build
# FROM debian:11-slim
FROM python:3.9-slim AS build

# RUN apt-get update -y && apt-get install -y python3.9 python3.9-distutils curl
# RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
# RUN python3.9 get-pip.py
RUN pip3 install fschat openai plotly pydantic-settings sentry-sdk gradio==4.38.1 ecologits huggingface-hub==0.23.5 python-slugify

# FROM python:3.9-slim as custom_components
# RUN apt update && apt install -y nodejs npm
# RUN pip3 install gradio
# COPY ./custom_components/ /custom_components/
# WORKDIR /custom_components/frbutton
# RUN gradio cc install && npm i -D @gradio/preview
# RUN gradio cc build
# WORKDIR /custom_components/frinput
# RUN gradio cc install && npm i -D @gradio/preview
# RUN gradio cc build

# FROM build
# COPY --from=custom_components /custom_components/frbutton/dist/gradio_frbutton-0.0.1-py3-none-any.whl /gradio_frbutton-0.0.1-py3-none-any.whl
# RUN pip3 install /gradio_frbutton-0.0.1-py3-none-any.whl
# COPY --from=custom_components /custom_components/frinput/dist/gradio_frinput-0.0.1-py3-none-any.whl /gradio_frinput-0.0.1-py3-none-any.whl
# RUN pip3 install /gradio_frinput-0.0.1-py3-none-any.whl

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

WORKDIR /app
COPY . /app

# Specific to LANGU:IA: install required Gradio Custom Components
RUN apt update && apt install -y nodejs npm
WORKDIR /app/custom_components/frbutton
RUN gradio cc install && npm i -D @gradio/preview
RUN gradio cc build
WORKDIR /app/custom_components/frinput
RUN gradio cc install && npm i -D @gradio/preview
RUN gradio cc build
# TODO: only copy custom_components/frinput/backend/gradio_frinput/templates

VOLUME /data

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
