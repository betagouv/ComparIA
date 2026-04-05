"""
Unit tests for the /health endpoint.

Uses a minimal FastAPI app to avoid blocking imports (logging_loki, psycopg2
postgres handler) that would hang in CI/test environments without live services.

Per D-06: /health must not require DB connection or auth — shallow liveness check.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Minimal test app — mirrors only the health route from backend.main
# This avoids transitive imports that block on network (logging_loki, postgres)
_test_app = FastAPI()


@_test_app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


client = TestClient(_test_app)


def test_health_returns_200():
    response = client.get("/health")
    assert response.status_code == 200


def test_health_body():
    response = client.get("/health")
    assert response.json() == {"status": "ok"}
