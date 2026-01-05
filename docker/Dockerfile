# Multi-stage build avec buildx optimisation
FROM public.ecr.aws/docker/library/python:3.13-slim AS base

# Install runtime dependencies seulement
RUN apt-get update -y && apt-get install -y curl postgresql-client && rm -rf /var/lib/apt/lists/*

FROM base AS builder
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

FROM base AS runtime
ENV PATH="/app/.venv/bin:/root/.local/bin/:$PATH"

# Copier seulement le nécessaire pour le runtime
COPY --from=builder /app/.venv /app/.venv
COPY controller.py main.py /app/
COPY utils /app/utils
COPY templates /app/templates
COPY languia /app/languia

WORKDIR /app
VOLUME /data
EXPOSE 80

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]