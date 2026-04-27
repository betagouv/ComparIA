"""Output normalizer for CompaRAG Tool Arena.

Produces a canonical NormalizedEnvelope from heterogeneous RAG tool output.
Pipeline position: post-dispatch, pre-sanitize (D-06).

All RAG tool outputs are normalized to {answer, sources, confidence, latency_ms}
before reaching the blind display layer (D-04).
"""

import json
from typing import Any

from pydantic import BaseModel


class Source(BaseModel):
    """Structured source object for RAG citations (D-07).

    All fields are optional — not all RAG tools provide rich citation metadata.
    """

    url: str | None = None
    title: str | None = None
    snippet: str | None = None
    page: int | None = None


class NormalizedEnvelope(BaseModel):
    """Canonical output envelope for any RAG tool response.

    normalized_fields tracks which fields were defaulted (not provided by the tool)
    so downstream consumers know which values are real vs synthesized (D-05).
    """

    answer: str
    sources: list[Source] = []
    confidence: float | None = None
    latency_ms: int = 0
    normalized_fields: list[str] = []  # fields that were defaulted (D-05)


def _parse_sources(raw_sources: Any) -> list[Source]:
    """Parse sources from raw JSON value into list[Source]."""
    if not isinstance(raw_sources, list):
        return []
    result = []
    for item in raw_sources:
        if isinstance(item, dict):
            result.append(Source(
                url=item.get("url"),
                title=item.get("title"),
                snippet=item.get("snippet"),
                page=item.get("page"),
            ))
        elif isinstance(item, str):
            result.append(Source(url=item))
    return result


def normalize_output(raw_text: str, duration_ms: int) -> NormalizedEnvelope:
    """Normalize raw MCP tool output to a canonical NormalizedEnvelope.

    Normalization strategy:
    1. Try json.loads(raw_text) — if valid JSON with "answer" key, extract known fields.
    2. For each missing field (sources, confidence, latency_ms), use default and append
       field name to normalized_fields so downstream knows which values are defaulted.
    3. If raw_text is not JSON or has no "answer" key, treat entire raw_text as the
       answer and default all other fields.
    4. latency_ms defaults to the duration_ms parameter if not present in JSON.

    Args:
        raw_text: Raw string output from the MCP tool.
        duration_ms: Measured duration of the MCP call — used as latency_ms fallback.

    Returns:
        NormalizedEnvelope with all required fields populated.
    """
    normalized_fields: list[str] = []

    # Attempt JSON parsing
    parsed: dict | None = None
    try:
        candidate = json.loads(raw_text)
        if isinstance(candidate, dict) and "answer" in candidate:
            parsed = candidate
    except (json.JSONDecodeError, ValueError):
        pass

    if parsed is None:
        # Plain text or JSON without "answer" key — treat entire raw_text as answer
        normalized_fields.extend(["sources", "confidence", "latency_ms"])
        return NormalizedEnvelope(
            answer=raw_text,
            sources=[],
            confidence=None,
            latency_ms=duration_ms,
            normalized_fields=normalized_fields,
        )

    # Extract known fields from parsed JSON
    answer: str = parsed["answer"]

    # sources
    if "sources" in parsed:
        sources = _parse_sources(parsed["sources"])
    else:
        sources = []
        normalized_fields.append("sources")

    # confidence
    if "confidence" in parsed:
        confidence = parsed["confidence"]
    else:
        confidence = None
        normalized_fields.append("confidence")

    # latency_ms
    if "latency_ms" in parsed:
        latency_ms = int(parsed["latency_ms"])
    else:
        latency_ms = duration_ms
        normalized_fields.append("latency_ms")

    return NormalizedEnvelope(
        answer=answer,
        sources=sources,
        confidence=confidence,
        latency_ms=latency_ms,
        normalized_fields=normalized_fields,
    )
