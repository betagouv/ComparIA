FROM nvidia/cuda:12.2.0-runtime-ubuntu20.04
# FROM debian:11-slim
# FROM python:3.9-slim

RUN apt-get update -y && apt-get install -y python3.9 python3.9-distutils curl
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
# TODO: virtualenv
RUN python3.9 get-pip.py
RUN pip3 install fschat
RUN pip3 install fschat[model_worker,webui]
RUN pip3 install openai plotly pydantic-settings sentry-sdk

WORKDIR /app

COPY . /app
VOLUME /data

EXPOSE 80

CMD ["python3.9", "-m", "fastchat.serve.gradio_web_server_multi_languia", "--controller-url", "http://fastchat-controller:21001", "--register-api-endpoint-file", "/register-api-endpoint-file.json", "--host", "0.0.0.0", "--port", "80"]