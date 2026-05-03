"""Document library registry for CompaRAG Tool Arena.

Mirrors MCPRegistry pattern: manifest-driven in-memory singleton loaded at import time.
"""

import json
from pathlib import Path

from pydantic import BaseModel

# backend/tool_arena/ -> CompaRAG/
ROOT_DIR = Path(__file__).parent.parent.parent
DOCUMENTS_INDEX_PATH = ROOT_DIR / "documents_index.json"


class DocumentConfig(BaseModel):
    """Internal registry entry — includes loaded content."""

    id: str
    title: str
    description: str
    content: str


class DocumentSummary(BaseModel):
    """List-endpoint response shape (per 11-UI-SPEC.md — DOC-02)."""

    id: str
    title: str
    description: str


class DocumentDetail(BaseModel):
    """Detail-endpoint response shape (per 11-UI-SPEC.md — DOC-03)."""

    id: str
    title: str
    description: str
    content: str


def load_documents(
    path: Path | None = None,
    root_dir: Path | None = None,
) -> list[DocumentConfig]:
    """Load and validate document configurations from a JSON manifest file.

    Args:
        path: Path to the JSON manifest file. Defaults to DOCUMENTS_INDEX_PATH
              (CompaRAG/documents_index.json).
        root_dir: Root directory used to resolve document file paths. Defaults
                  to ROOT_DIR (CompaRAG/). Override in tests via tmp_path.

    Returns:
        list[DocumentConfig]: List of documents with content loaded into memory.

    Raises:
        FileNotFoundError: If the manifest file does not exist.
        json.JSONDecodeError: If the manifest contains malformed JSON.
        FileNotFoundError: If a manifest entry references a missing document file.
        pydantic.ValidationError: If any manifest entry fails field validation.
    """
    if path is None:
        path = DOCUMENTS_INDEX_PATH
    if root_dir is None:
        root_dir = ROOT_DIR

    if not path.exists():
        raise FileNotFoundError(f"Document manifest not found at {path}")

    with open(path) as f:
        raw = json.load(f)  # raises json.JSONDecodeError on malformed JSON

    docs = []
    for entry in raw:
        file_path = root_dir / entry["file"]
        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")
        content = file_path.read_text(encoding="utf-8")
        docs.append(
            DocumentConfig(
                id=entry["id"],
                title=entry["title"],
                description=entry["description"],
                content=content,
            )
        )
    return docs


class DocumentRegistry:
    """Singleton registry of documents loaded from documents_index.json.

    Instantiated at module level so config errors propagate at import time
    before FastAPI accepts any requests (mirrors MCPRegistry pattern).
    """

    def __init__(self, docs: list[DocumentConfig]) -> None:
        self._docs: dict[str, DocumentConfig] = {d.id: d for d in docs}

    def list_all(self) -> list[DocumentConfig]:
        """Return all registered documents."""
        return list(self._docs.values())

    def get(self, doc_id: str) -> DocumentConfig | None:
        """Return a document by id, or None if not found."""
        return self._docs.get(doc_id)

    @property
    def document_ids(self) -> list[str]:
        """List all registered document IDs."""
        return list(self._docs.keys())

    def __len__(self) -> int:
        return len(self._docs)


# Module-level singleton — raises at import time if manifest is missing or malformed
# Mirrors: registry = MCPRegistry(load_mcp_servers()) in registry.py
document_registry = DocumentRegistry(load_documents())
