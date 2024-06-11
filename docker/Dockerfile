FROM nvidia/cuda:12.2.0-runtime-ubuntu20.04
# FROM debian:11-slim
# FROM python:3.9-slim

RUN apt-get update -y && apt-get install -y python3.9 python3.9-distutils curl
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
# TODO: virtualenv
RUN python3.9 get-pip.py

RUN groupadd fastchat --gid 10001 && useradd --system -u 10001 --gid 10001 --home /app fastchat
USER fastchat
COPY --chown=fastchat:fastchat . /app
WORKDIR /app

RUN pip3 install -e ".[webui,model_worker]"

# For monitoring
RUN pip3 install plotly

# For OpenAI-like APIs
RUN pip3 install openai

# TODO: distroless virtualenv and multistage build
# FROM gcr.io/distroless/python3-debian11