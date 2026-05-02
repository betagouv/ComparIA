"""LlamaIndex RAG MCP Server — FastMCP on port 8011 (or $PORT).

Full RAG pipeline: VectorStoreIndex over the corpus + query_engine that
synthesizes an answer via an LLM (mistral-small via OpenRouter by default).
Returns a finished answer to the dispatcher — no post-hoc mediation needed.
"""

import os
from pathlib import Path

from fastmcp import FastMCP
from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.litellm import LiteLLM
from starlette.requests import Request
from starlette.responses import PlainTextResponse

CORPUS_DIR = Path(__file__).parent.parent / "corpus"
LLM_MODEL = os.getenv(
    "LLAMAINDEX_RAG_LLM_ID", "openrouter/mistralai/mistral-small-3.1-24b-instruct"
)

mcp = FastMCP("LlamaIndex RAG")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


print("Loading corpus and building VectorStoreIndex...")
Settings.embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
Settings.llm = LiteLLM(
    model=LLM_MODEL,
    api_key=os.environ["OPENROUTER_API_KEY"],
    max_tokens=1024,
    temperature=0.2,
)
documents = SimpleDirectoryReader(str(CORPUS_DIR)).load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine(similarity_top_k=3)
print(f"Index ready: {len(documents)} documents loaded")


def _format_sources(source_nodes) -> str:
    return ", ".join(
        sorted(
            {
                Path(n.metadata.get("file_name", "unknown")).stem
                for n in source_nodes
                if n.metadata.get("file_name")
            }
        )
    )


@mcp.tool()
def rag_query(task: str, goal: str, document_content: str = "") -> str:
    """Answer a question using full RAG (retrieval + generation) over the
    static corpus, or over an uploaded document if document_content is set.
    """
    from llama_index.core import Document as LIDocument

    query = f"{task} {goal}"

    if document_content.strip():
        doc = LIDocument(text=document_content, metadata={"file_name": "uploaded"})
        ephemeral_index = VectorStoreIndex.from_documents([doc])
        response = ephemeral_index.as_query_engine(similarity_top_k=3).query(query)
    else:
        response = query_engine.query(query)

    answer = str(response).strip()
    if not answer:
        return "No relevant documents found for this query."

    sources = _format_sources(getattr(response, "source_nodes", []))
    source_str = f"Sources: {sources}\n\n" if sources else ""
    return f"{source_str}{answer}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.getenv("PORT", 8011)))
