# Multi-stage build avec buildx optimisation
# Mettre à jour UV_VERSION si nécessaire
ARG UV_VERSION=0.7.2
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM public.ecr.aws/docker/library/python:3.13-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

FROM public.ecr.aws/docker/library/python:3.13-slim AS runtime

# Install runtime dependencies
RUN apt-get update -y && apt-get install -y curl postgresql-client && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /usr/local/bin/uv

ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app

# Copier le venv et le code
COPY --from=builder /app/.venv /app/.venv
COPY pyproject.toml uv.lock ./
COPY controller.py /app/
COPY backend /app/backend
COPY utils /app/utils
COPY templates /app/templates

VOLUME /data
EXPOSE 80

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "80"]