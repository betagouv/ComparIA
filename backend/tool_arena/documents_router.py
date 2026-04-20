"""
Document library sub-router (DOC-02, DOC-03).

Isolated from the main router so tests can import this without
pulling in the psycopg2/Redis dependency chain via dispatcher.py.
"""

from fastapi import APIRouter, HTTPException, Response

from backend.tool_arena.documents import (
    DocumentDetail,
    DocumentSummary,
    document_registry,
)

documents_router = APIRouter()

_DOCUMENTS_CACHE_CONTROL = "public, max-age=3600, stale-while-revalidate=86400"


@documents_router.get("/documents")
async def list_documents(response: Response):
    """Return catalogue of available documents (id, title, description — no content).

    Per DOC-02: unauthenticated, cacheable.
    """
    response.headers["Cache-Control"] = _DOCUMENTS_CACHE_CONTROL
    return [
        DocumentSummary(id=d.id, title=d.title, description=d.description)
        for d in document_registry.list_all()
    ]


@documents_router.get("/documents/{doc_id}")
async def get_document(doc_id: str, response: Response):
    """Return a single document by id including full content.

    Per DOC-03: unauthenticated, cacheable. HTTP 404 when doc_id is unknown.
    """
    doc = document_registry.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    response.headers["Cache-Control"] = _DOCUMENTS_CACHE_CONTROL
    return DocumentDetail(
        id=doc.id,
        title=doc.title,
        description=doc.description,
        content=doc.content,
    )
