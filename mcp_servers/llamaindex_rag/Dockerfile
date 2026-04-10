# Stage 1: builder — install deps + pre-download HF model
FROM python:3.12-slim AS builder

WORKDIR /app

RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY mcp_servers/llamaindex_rag/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download sentence-transformers model (per D-02)
ENV HF_HOME=/app/.cache/huggingface
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Stage 2: runtime
FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"
ENV HF_HOME=/app/.cache/huggingface

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/.cache /app/.cache

# Bake corpus into image (per D-01)
COPY mcp_servers/corpus /app/corpus

# Copy server source
COPY mcp_servers/llamaindex_rag/server.py /app/llamaindex_rag/server.py

EXPOSE 8011

CMD fastmcp run llamaindex_rag/server.py --transport streamable-http --host 0.0.0.0 --port ${PORT:-8011}
