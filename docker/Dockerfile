FROM public.ecr.aws/docker/library/python:3.13-slim AS base

# Debug tools
RUN apt-get update -y && apt-get install -y curl postgresql-client git

ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/app/.venv/bin:/root/.local/bin/:$PATH"

COPY ./pyproject.toml /app/pyproject.toml
WORKDIR /app
RUN uv sync

VOLUME /data

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

COPY controller.py main.py /app/
# Useful for export scripts
COPY utils /app/utils
COPY templates /app/templates
COPY languia /app/languia
