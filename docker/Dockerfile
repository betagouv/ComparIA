FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS base
# FROM public.ecr.aws/docker/library/python:3.11-slim AS base
# COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Debug tools
RUN apt-get update -y && apt-get install -y curl postgresql-client git
COPY ./pyproject.toml pyproject.toml

WORKDIR /app

VOLUME /data

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]

# Specific to compar:IA: install required Gradio Custom Components
# Comment the next line if you want a main image with node
# FROM node:22 AS cc
FROM base AS cc
RUN apt update && apt install -y nodejs npm

COPY custom_components /app/custom_components

# # Install dependencies, including @gouvfr/dsfr (if needed globally)
# COPY custom_components/customchatbot/frontend/package.json ./
# RUN npm install

RUN pip install gradio

RUN gradio cc install custom_components/customradiocard
RUN gradio cc install custom_components/frinput
RUN gradio cc install custom_components/customchatbot
RUN gradio cc install custom_components/customdropdown

RUN gradio cc build custom_components/customradiocard --no-generate-docs --bump-version
RUN gradio cc build custom_components/frinput --no-generate-docs --bump-version
RUN gradio cc build custom_components/customchatbot --no-generate-docs --bump-version
RUN gradio cc build custom_components/customdropdown --no-generate-docs --bump-version

# Comment this line if you want an image with node
FROM base AS app
COPY --from=cc /app/custom_components /app/custom_components
RUN uv sync

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

COPY controller.py main.py demo.py models-extra-info.toml /app/
# Useful for export scripts
COPY utils /app/utils
COPY templates /app/templates
COPY assets /app/assets
COPY languia /app/languia
