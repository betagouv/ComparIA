"""LangChain RAG MCP Server — FastMCP on port 8010."""

from pathlib import Path

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

CORPUS_DIR = Path(__file__).parent.parent / "corpus"

mcp = FastMCP("LangChain RAG")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


# Build index at startup
print("Loading corpus and building FAISS index...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
loader = DirectoryLoader(str(CORPUS_DIR), glob="*.md", loader_cls=TextLoader)
docs = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)
vectorstore = FAISS.from_documents(chunks, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
print(f"Index ready: {len(chunks)} chunks from {len(docs)} documents")


@mcp.tool()
def rag_query(task: str, goal: str, document_content: str = "") -> str:
    """Answer a question using RAG over a document or the static corpus.

    If document_content is provided, builds an ephemeral in-memory index from it.
    Otherwise falls back to the pre-built static corpus index.
    """
    from langchain_core.documents import Document as LCDocument

    query = f"{task} {goal}"

    if document_content.strip():
        doc = LCDocument(page_content=document_content, metadata={"source": "uploaded"})
        doc_chunks = splitter.split_documents([doc])
        if not doc_chunks:
            return "Document could not be split into chunks."
        ephemeral_store = FAISS.from_documents(doc_chunks, embeddings)
        results = ephemeral_store.as_retriever(search_kwargs={"k": 3}).invoke(query)
    else:
        results = retriever.invoke(query)

    if not results:
        return "No relevant documents found for this query."
    context = "\n\n---\n\n".join(doc.page_content for doc in results)
    sources = set(Path(doc.metadata.get("source", "unknown")).stem for doc in results)
    return f"Sources: {', '.join(sources)}\n\n{context}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8010)
