# Multi-stage build avec buildx optimisation
FROM public.ecr.aws/docker/library/python:3.13-slim AS builder

# Install curl (needed for uv installer) and uv
RUN apt-get update -y && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

FROM public.ecr.aws/docker/library/python:3.13-slim AS runtime

# Install runtime dependencies
RUN apt-get update -y && apt-get install -y curl postgresql-client && rm -rf /var/lib/apt/lists/*

# Copier uv depuis le builder
COPY --from=builder /root/.local/bin/uv /usr/local/bin/uv

ENV PATH="/app/.venv/bin:$PATH"
WORKDIR /app

# Copier le venv et le code
COPY --from=builder /app/.venv /app/.venv
COPY pyproject.toml uv.lock ./
COPY controller.py backend/main.py /app/
COPY utils /app/utils
COPY templates /app/templates
COPY languia /app/languia

VOLUME /data
EXPOSE 80

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]