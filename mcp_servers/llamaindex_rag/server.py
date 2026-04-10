"""LlamaIndex RAG MCP Server — FastMCP on port 8011 (or $PORT)."""

import os
from pathlib import Path

from fastmcp import FastMCP
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from starlette.requests import Request
from starlette.responses import PlainTextResponse

CORPUS_DIR = Path(__file__).parent.parent / "corpus"

mcp = FastMCP("LlamaIndex RAG")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

# Build index at startup
print("Loading corpus and building VectorStoreIndex...")
Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
Settings.llm = None  # retrieval only, no LLM synthesis
documents = SimpleDirectoryReader(str(CORPUS_DIR)).load_data()
index = VectorStoreIndex.from_documents(documents)
retriever = index.as_retriever(similarity_top_k=3)
print(f"Index ready: {len(documents)} documents loaded")


@mcp.tool()
def rag_query(task: str, goal: str, document_content: str = "") -> str:
    """Answer a question using RAG over a document or the static corpus.

    If document_content is provided, builds an ephemeral in-memory index from it.
    Otherwise falls back to the pre-built static corpus index.
    """
    from llama_index.core import Document as LIDocument

    query = f"{task} {goal}"

    if document_content.strip():
        doc = LIDocument(text=document_content, metadata={"file_name": "uploaded"})
        ephemeral_index = VectorStoreIndex.from_documents([doc])
        nodes = ephemeral_index.as_retriever(similarity_top_k=3).retrieve(query)
    else:
        nodes = retriever.retrieve(query)

    if not nodes:
        return "No relevant documents found for this query."
    context = "\n\n---\n\n".join(node.get_content() for node in nodes)
    sources = set(
        Path(node.metadata.get("file_name", "unknown")).stem
        for node in nodes
        if node.metadata.get("file_name")
    )
    source_str = f"Sources: {', '.join(sources)}\n\n" if sources else ""
    return f"{source_str}{context}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.getenv("PORT", 8011)))
