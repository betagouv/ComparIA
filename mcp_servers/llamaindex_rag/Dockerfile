FROM python:3.12-slim

WORKDIR /app

COPY mcp_servers/llamaindex_rag/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_servers/corpus /app/corpus
COPY mcp_servers/llamaindex_rag/server.py /app/llamaindex_rag/server.py

EXPOSE 8011

CMD python llamaindex_rag/server.py
