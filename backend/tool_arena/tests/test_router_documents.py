"""Integration tests for GET /tool-arena/documents and GET /tool-arena/documents/{doc_id}.

Uses a minimal FastAPI app wired to the real document_registry to avoid
transitive imports that block on network (psycopg2, Redis, MCP dispatcher).

Per 11-02-PLAN:
  - List endpoint returns DocumentSummary objects (no content field)
  - Detail endpoint returns DocumentDetail (includes content)
  - Unknown doc_id returns 404 with informative detail
"""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.tool_arena.documents import (
    DocumentDetail,
    DocumentSummary,
    document_registry,
)

# ---------------------------------------------------------------------------
# Minimal test app — only the two document routes
# ---------------------------------------------------------------------------

_test_app = FastAPI()


@_test_app.get("/tool-arena/documents", response_model=list[DocumentSummary])
async def list_documents():
    return [
        DocumentSummary(id=d.id, title=d.title, description=d.description)
        for d in document_registry.list_all()
    ]


@_test_app.get("/tool-arena/documents/{doc_id}", response_model=DocumentDetail)
async def get_document(doc_id: str):
    doc = document_registry.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
    return DocumentDetail(
        id=doc.id,
        title=doc.title,
        description=doc.description,
        content=doc.content,
    )


client = TestClient(_test_app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_list_documents_returns_200_and_no_content_field():
    """List endpoint returns 200 and every item lacks a 'content' field."""
    response = client.get("/tool-arena/documents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for item in data:
        assert "content" not in item, f"'content' should not be in list response, got: {item}"
        assert "id" in item
        assert "title" in item
        assert "description" in item


def test_list_documents_returns_all_entries():
    """List endpoint returns one entry per document in the registry."""
    response = client.get("/tool-arena/documents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == len(document_registry)


def test_get_document_known_returns_200_and_content():
    """Detail endpoint for a known doc returns 200 with non-empty content."""
    first_id = document_registry.document_ids[0]
    response = client.get(f"/tool-arena/documents/{first_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == first_id
    assert "content" in data
    assert len(data["content"]) > 0


def test_get_document_unknown_returns_404():
    """Detail endpoint for an unknown doc_id returns 404 with doc_id in detail."""
    response = client.get("/tool-arena/documents/nonexistent_id_xyz")
    assert response.status_code == 404
    detail = response.json().get("detail", "")
    assert "nonexistent_id_xyz" in detail
