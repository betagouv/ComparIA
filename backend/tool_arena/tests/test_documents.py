"""Unit tests for backend.tool_arena.documents — loader and registry."""

import json
from pathlib import Path

import pytest

from backend.tool_arena.documents import (
    DocumentConfig,
    DocumentRegistry,
    load_documents,
)


def _write_manifest(tmp_path: Path, entries: list[dict]) -> Path:
    manifest_path = tmp_path / "documents_index.json"
    manifest_path.write_text(json.dumps(entries))
    return manifest_path


def test_load_documents_returns_all_entries(tmp_path):
    (tmp_path / "doc1.txt").write_text("Hello document one", encoding="utf-8")
    manifest_path = _write_manifest(tmp_path, [
        {"id": "doc1", "title": "Doc One", "description": "First doc", "file": "doc1.txt"}
    ])
    docs = load_documents(path=manifest_path, root_dir=tmp_path)
    assert len(docs) == 1
    assert docs[0].id == "doc1"
    assert docs[0].title == "Doc One"
    assert docs[0].description == "First doc"
    assert docs[0].content == "Hello document one"


def test_load_documents_missing_manifest_raises(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError, match="Document manifest not found"):
        load_documents(path=missing, root_dir=tmp_path)


def test_load_documents_malformed_json_raises(tmp_path):
    bad = tmp_path / "documents_index.json"
    bad.write_text("{not valid json")
    with pytest.raises(json.JSONDecodeError):
        load_documents(path=bad, root_dir=tmp_path)


def test_load_documents_missing_referenced_file_raises(tmp_path):
    manifest_path = _write_manifest(tmp_path, [
        {"id": "x", "title": "X", "description": "d", "file": "missing.txt"}
    ])
    with pytest.raises(FileNotFoundError, match="Document file not found"):
        load_documents(path=manifest_path, root_dir=tmp_path)


def test_load_documents_preserves_utf8(tmp_path):
    (tmp_path / "u.txt").write_text("café — 中文 — emoji 🎯", encoding="utf-8")
    manifest_path = _write_manifest(tmp_path, [
        {"id": "u", "title": "U", "description": "d", "file": "u.txt"}
    ])
    docs = load_documents(path=manifest_path, root_dir=tmp_path)
    assert docs[0].content == "café — 中文 — emoji 🎯"


def test_registry_list_all_returns_all_docs():
    docs = [
        DocumentConfig(id="a", title="A", description="a", content="ca"),
        DocumentConfig(id="b", title="B", description="b", content="cb"),
    ]
    registry = DocumentRegistry(docs)
    ids = sorted(d.id for d in registry.list_all())
    assert ids == ["a", "b"]


def test_registry_get_unknown_returns_none():
    registry = DocumentRegistry([])
    assert registry.get("missing") is None


def test_registry_get_known_returns_doc():
    doc = DocumentConfig(id="x", title="X", description="d", content="c")
    registry = DocumentRegistry([doc])
    assert registry.get("x") is doc


def test_registry_len():
    docs = [
        DocumentConfig(id="a", title="A", description="d", content="c"),
        DocumentConfig(id="b", title="B", description="d", content="c"),
        DocumentConfig(id="c", title="C", description="d", content="c"),
    ]
    assert len(DocumentRegistry(docs)) == 3
