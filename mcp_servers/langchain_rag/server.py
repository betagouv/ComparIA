"""LangChain RAG MCP Server — FastMCP on port 8010 (or $PORT)."""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate

CORPUS_DIR = Path(__file__).parent.parent / "corpus"

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

llm = ChatOpenAI(
    model="mistralai/mistral-small",
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

embeddings = OpenAIEmbeddings(
    model="openai/text-embedding-3-small",
    base_url="https://openrouter.ai/api/v1",
    openai_api_key=OPENROUTER_API_KEY,
)

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

_PROMPT = ChatPromptTemplate.from_template(
    "You are a helpful assistant. Answer the question using ONLY the context below. "
    "If the context does not contain enough information, say so.\n\n"
    "Context:\n{context}\n\n"
    "Question: {query}\n\n"
    "Answer:"
)

# Set after lifespan build
retriever = None


@asynccontextmanager
async def lifespan(app):
    global retriever
    print("Loading corpus and building FAISS index...")
    loop = asyncio.get_event_loop()
    loader = DirectoryLoader(str(CORPUS_DIR), glob="*.md", loader_cls=TextLoader)
    docs = loader.load()
    chunks = splitter.split_documents(docs)
    vectorstore = await loop.run_in_executor(
        None, lambda: FAISS.from_documents(chunks, embeddings)
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    print(f"Index ready: {len(chunks)} chunks from {len(docs)} documents")
    yield


mcp = FastMCP("LangChain RAG", lifespan=lifespan)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


@mcp.tool()
def rag_query(task: str, goal: str, document_content: str = "") -> str:
    """Answer a question using RAG over a document or the static corpus, synthesized by Mistral Small.

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
        if retriever is None:
            return "Index not ready yet, please retry in a moment."
        results = retriever.invoke(query)

    if not results:
        return "No relevant documents found for this query."

    context = "\n\n---\n\n".join(doc.page_content for doc in results)
    sources = set(Path(doc.metadata.get("source", "unknown")).stem for doc in results)

    messages = _PROMPT.format_messages(context=context, query=query)
    answer = llm.invoke(messages)

    return f"Sources: {', '.join(sources)}\n\n{answer.content}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.getenv("PORT", 8010)), path="/mcp")
