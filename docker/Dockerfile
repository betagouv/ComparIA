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

FROM base AS app

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

COPY . /app

# Specific to Compar:IA: install required Gradio Custom Components
# Comment the next line if you want an image with node
FROM base AS cc
RUN apt update && apt install -y nodejs npm
COPY --from=app /app/custom_components /app/custom_components
# TODO: factorize this
WORKDIR /app/custom_components/customradiocard
RUN gradio cc install
RUN gradio cc build --no-generate-docs --bump-version
WORKDIR /app/custom_components/frinput
RUN gradio cc install
# # workaround
# RUN npm install @gouvfr/dsfr
RUN gradio cc build --no-generate-docs --bump-version
# WORKDIR /app/custom_components/frslider
# RUN gradio cc install
# # workaround
# RUN npm install @gouvfr/dsfr
# RUN gradio cc build --no-generate-docs --bump-version
# WORKDIR /app/custom_components/customslider
# RUN gradio cc install
# RUN npm install @gouvfr/dsfr
# RUN gradio cc build --no-generate-docs --bump-version

# Comment these 2 lines if you want an image with node
FROM app
COPY --from=cc /app/custom_components /app/custom_components
