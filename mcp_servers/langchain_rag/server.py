"""LangChain RAG MCP Server — FastMCP on port 8010 (or $PORT).

Full RAG pipeline: retrieves chunks via FAISS then synthesizes an answer via
an LLM (mistral-small via OpenRouter by default). Returns a finished answer
to the dispatcher — no post-hoc mediation needed.
"""

import os
from pathlib import Path

from fastmcp import FastMCP
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from starlette.requests import Request
from starlette.responses import PlainTextResponse

CORPUS_DIR = Path(__file__).parent.parent / "corpus"
LLM_MODEL = os.getenv("LANGCHAIN_RAG_LLM_ID", "mistralai/mistral-small-3.1-24b-instruct")

mcp = FastMCP("LangChain RAG")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


print("Loading corpus and building FAISS index...")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
loader = DirectoryLoader(str(CORPUS_DIR), glob="*.md", loader_cls=TextLoader)
docs = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)
vectorstore = FAISS.from_documents(chunks, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
print(f"Index ready: {len(chunks)} chunks from {len(docs)} documents")

llm = ChatOpenAI(
    model=LLM_MODEL,
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
    max_tokens=1024,
    temperature=0.2,
)

ANSWER_PROMPT = ChatPromptTemplate.from_template(
    """You are answering a user's task using context retrieved from documents.

Stay grounded: only use facts present in the context. If the context does not address the task, say so explicitly rather than fabricating.
Write a clear, well-structured answer covering the relevant points. Preserve concrete details (numbers, names, dates, examples). Avoid one-sentence answers when the context supports more.

Task: {task}
Goal: {goal}

Context:
{context}

Answer:"""
)


def _format_sources(documents) -> str:
    return ", ".join(
        sorted({Path(d.metadata.get("source", "unknown")).stem for d in documents})
    )


@mcp.tool()
def rag_query(task: str, goal: str, document_content: str = "") -> str:
    """Answer a question using full RAG (retrieval + generation) over the
    static corpus, or over an uploaded document if document_content is set.
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

    context = "\n\n---\n\n".join(d.page_content for d in results)
    prompt = ANSWER_PROMPT.format_messages(task=task, goal=goal, context=context)
    answer = llm.invoke(prompt).content or ""
    sources = _format_sources(results)
    return f"Sources: {sources}\n\n{answer}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.getenv("PORT", 8010)))
