# FROM nvidia/cuda:12.2.0-runtime-ubuntu20.04 AS build
# FROM debian:11-slim
FROM python:3.10-slim AS base

# RUN apt-get update -y && apt-get install -y python3.9 python3.9-distutils curl
# RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
# RUN python3.9 get-pip.py
COPY ./requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt
WORKDIR /app

VOLUME /data

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]

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
FROM base AS app

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

COPY . /app

# Specific to LANGU:IA: install required Gradio Custom Components
# Comment the next line if you want an image with node
FROM base AS cc
RUN apt update && apt install -y nodejs npm
COPY --from=app /app /app
WORKDIR /app/custom_components/frbutton
RUN gradio cc install
RUN gradio cc build --no-generate-docs
WORKDIR /app/custom_components/frinput
RUN gradio cc install
RUN gradio cc build --no-generate-docs
WORKDIR /app/custom_components/frslider
RUN gradio cc install
RUN gradio cc build --no-generate-docs

# Comment these 2 lines if you want an image with node
FROM app
COPY --from=cc /app/custom_components /app/custom_components
