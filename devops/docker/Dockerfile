# Multi-stage build avec buildx optimisation
# Mettre à jour UV_VERSION si nécessaire
ARG UV_VERSION=0.7.2
FROM ghcr.io/astral-sh/uv:${UV_VERSION}@sha256:3b898ca84fbe7628c5adcd836c1de78a0f1ded68344d019af8478d4358417399 AS uv

FROM public.ecr.aws/docker/library/python:3.13-slim@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a AS builder
COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --group data

FROM public.ecr.aws/docker/library/python:3.13-slim@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a AS runtime

# Install runtime dependencies and a non-root user to run the app as
RUN apt-get update -y && apt-get install -y curl postgresql-client && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app && useradd --system --gid app --home-dir /app --create-home --shell /usr/sbin/nologin app

COPY --from=uv /uv /usr/local/bin/uv

ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app

# Copier le venv et le code
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app pyproject.toml uv.lock ./
COPY --chown=app:app backend /app/backend
COPY --chown=app:app utils /app/utils
COPY --chown=app:app alembic.ini /app/
COPY --chown=app:app comparia-cli /app/
COPY --chown=app:app data /app/data

RUN mkdir -p /data && chown app:app /data
VOLUME /data
EXPOSE 80

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

USER app

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "80"]