FROM public.ecr.aws/docker/library/python:3.13-slim AS base

# Debug tools
RUN apt-get update -y && apt-get install -y curl postgresql-client git

# Create a non-root user with the same UID/GID as the host user (1000 is common)
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} app && \
    useradd -m -u ${USER_ID} -g app app

ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/app/.venv/bin:/root/.local/bin/:$PATH"

COPY --chown=app:app ./pyproject.toml /app/pyproject.toml
WORKDIR /app
USER app
RUN uv sync

VOLUME /data

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

COPY controller.py main.py demo.py /app/
# Useful for export scripts
COPY utils /app/utils
COPY templates /app/templates
COPY languia /app/languia
