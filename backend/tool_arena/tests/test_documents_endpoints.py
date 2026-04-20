"""Endpoint tests for document library routes (DOC-02, DOC-03).

Tests exercise the REAL router imported from backend.tool_arena.router,
mounted on a minimal FastAPI app to avoid pulling in the full backend
(DB/Redis) dependency chain.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.tool_arena.router import router

_EXPECTED_CACHE_CONTROL = "public, max-age=3600, stale-while-revalidate=86400"
_EXPECTED_IDS = {"rag_overview", "langchain_concepts", "llamaindex_concepts"}


@pytest.fixture(scope="module")
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_list_documents_returns_200_with_all_ids(client):
    resp = client.get("/tool-arena/documents")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    ids = {item["id"] for item in body}
    assert _EXPECTED_IDS.issubset(ids), f"missing ids: {_EXPECTED_IDS - ids}"
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
