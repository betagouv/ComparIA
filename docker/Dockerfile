FROM public.ecr.aws/docker/library/python:3.11-slim AS base

# Debug tools
RUN apt-get update -y && apt-get install -y curl postgresql-client
COPY ./requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt
WORKDIR /app

VOLUME /data

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]

# Specific to compar:IA: install required Gradio Custom Components
# Comment the next line if you want a main image with node
FROM base AS cc
RUN apt update && apt install -y nodejs npm
COPY custom_components /app/custom_components

# TODO: factorize this
WORKDIR /app/custom_components/customradiocard
RUN gradio cc install
RUN gradio cc build --no-generate-docs --bump-version

WORKDIR /app/custom_components/frinput
RUN gradio cc install
RUN gradio cc build --no-generate-docs --bump-version

WORKDIR /app/custom_components/customchatbot
RUN gradio cc install
# workaround
RUN npm install @gouvfr/dsfr
RUN gradio cc build --no-generate-docs --bump-version

WORKDIR /app/custom_components/customdropdown
RUN gradio cc install
RUN gradio cc build --no-generate-docs --bump-version

# Comment this line if you want an image with node
FROM base AS app
COPY --from=cc /app/custom_components /app/custom_components

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

COPY controller.py main.py demo.py models-extra-info.toml /app/
# Useful for export scripts
COPY utils /app/utils
COPY templates /app/templates
COPY assets /app/assets
COPY languia /app/languia
