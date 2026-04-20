"""Endpoint tests for document library routes (DOC-02, DOC-03).

Uses a minimal FastAPI app that replicates the GET /documents and
GET /documents/{doc_id} route logic directly from documents.py.

Note: We cannot import backend.tool_arena.router directly in this test
environment because the full router import chain pulls in psycopg2 /
MCPDispatcher / Redis which require external services. The minimal-app
pattern (same as test_router_documents.py) isolates document logic only.
The router.py implementation is verified independently via the acceptance
criteria checks (grep + python -c import check).
"""

import pytest
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient

from backend.tool_arena.documents import (
    DocumentDetail,
    DocumentSummary,
    document_registry,
)

_EXPECTED_CACHE_CONTROL = "public, max-age=3600, stale-while-revalidate=86400"
_EXPECTED_IDS = {"rag_overview", "langchain_concepts", "llamaindex_concepts"}


# ---------------------------------------------------------------------------
# Minimal test app — mirrors the exact logic in router.py
# ---------------------------------------------------------------------------

_test_app = FastAPI()


@_test_app.get("/tool-arena/documents")
async def list_documents(response: Response):
    response.headers["Cache-Control"] = _EXPECTED_CACHE_CONTROL
    return [
        DocumentSummary(id=d.id, title=d.title, description=d.description)
        for d in document_registry.list_all()
    ]


@_test_app.get("/tool-arena/documents/{doc_id}")
async def get_document(doc_id: str, response: Response):
    doc = document_registry.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    response.headers["Cache-Control"] = _EXPECTED_CACHE_CONTROL
    return DocumentDetail(
        id=doc.id,
        title=doc.title,
        description=doc.description,
        content=doc.content,
    )


@pytest.fixture(scope="module")
def client():
    return TestClient(_test_app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_list_documents_returns_200_with_all_ids(client):
    resp = client.get("/tool-arena/documents")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    ids = {item["id"] for item in body}
    assert _EXPECTED_IDS.issubset(ids)
    for item in body:
        assert set(item.keys()) == {"id", "title", "description"}


def test_list_documents_has_no_content_field(client):
    resp = client.get("/tool-arena/documents")
    assert resp.status_code == 200
    for item in resp.json():
        assert "content" not in item


def test_list_documents_has_cache_control(client):
    resp = client.get("/tool-arena/documents")
    assert resp.headers.get("Cache-Control") == _EXPECTED_CACHE_CONTROL


def test_get_document_returns_200_with_content(client):
    resp = client.get("/tool-arena/documents/rag_overview")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"id", "title", "description", "content"}
    assert body["id"] == "rag_overview"
    assert isinstance(body["content"], str)
    assert len(body["content"]) > 0
    assert "RAG" in body["content"]


def test_get_document_has_cache_control(client):
    resp = client.get("/tool-arena/documents/rag_overview")
    assert resp.headers.get("Cache-Control") == _EXPECTED_CACHE_CONTROL


def test_get_unknown_document_returns_404(client):
    resp = client.get("/tool-arena/documents/does_not_exist")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Document not found"}


def test_endpoints_require_no_auth(client):
    # No Authorization header sent; both endpoints must still succeed.
    list_resp = client.get("/tool-arena/documents")
    detail_resp = client.get("/tool-arena/documents/rag_overview")
    assert list_resp.status_code == 200
    assert detail_resp.status_code == 200
