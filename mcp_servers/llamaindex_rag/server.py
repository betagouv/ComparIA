"""LlamaIndex RAG MCP Server — FastMCP on port 8011 (or $PORT)."""

import os
from pathlib import Path

from fastmcp import FastMCP
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai_like import OpenAILike
from starlette.requests import Request
from starlette.responses import PlainTextResponse

CORPUS_DIR = Path(__file__).parent.parent / "corpus"

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

mcp = FastMCP("LlamaIndex RAG")

Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",
    api_base="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)
Settings.llm = OpenAILike(
    model="mistralai/mistral-small",
    api_base="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    is_chat_model=True,
)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


# Build index at startup
print("Loading corpus and building VectorStoreIndex...")
documents = SimpleDirectoryReader(str(CORPUS_DIR)).load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine(similarity_top_k=3)
print(f"Index ready: {len(documents)} documents loaded")


@mcp.tool()
def rag_query(task: str, goal: str, document_content: str = "") -> str:
    """Answer a question using RAG over a document or the static corpus, synthesized by Mistral Small.

    If document_content is provided, builds an ephemeral in-memory index from it.
    Otherwise falls back to the pre-built static corpus index.
    """
    from llama_index.core import Document as LIDocument

    query = f"{task} {goal}"

    if document_content.strip():
        doc = LIDocument(text=document_content, metadata={"file_name": "uploaded"})
        ephemeral_engine = VectorStoreIndex.from_documents([doc]).as_query_engine(similarity_top_k=3)
        response = ephemeral_engine.query(query)
    else:
        response = query_engine.query(query)

    sources = set(
        Path(n.metadata.get("file_name", "unknown")).stem
        for n in response.source_nodes
        if n.metadata.get("file_name")
    )
    source_str = f"Sources: {', '.join(sources)}\n\n" if sources else ""
    return f"{source_str}{response.response}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.getenv("PORT", 8011)), path="/mcp")
