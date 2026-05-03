FROM python:3.12-slim

WORKDIR /app

COPY mcp_servers/langchain_rag/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_servers/corpus /app/corpus
COPY mcp_servers/langchain_rag/server.py /app/langchain_rag/server.py

EXPOSE 8010

CMD python langchain_rag/server.py
