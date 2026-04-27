"""Unit tests for the output normalizer module (D-04 through D-07)."""

import json
import pytest

from backend.tool_arena.normalizer import NormalizedEnvelope, Source, normalize_output


# --------------------------------------------------------------------------- #
# Tests: normalize_output
# --------------------------------------------------------------------------- #

def test_full_envelope_passes_through():
    """Test 1: normalize_output with full envelope passes through unchanged, normalized_fields=[]."""
    raw = json.dumps({
        "answer": "The answer is 42.",
        "sources": [{"url": "https://example.com", "title": "Example", "snippet": "text", "page": 1}],
        "confidence": 0.95,
        "latency_ms": 120,
    })
    result = normalize_output(raw, duration_ms=150)
    assert result.answer == "The answer is 42."
    assert len(result.sources) == 1
    assert result.sources[0].url == "https://example.com"
    assert result.confidence == 0.95
    assert result.latency_ms == 120
    assert result.normalized_fields == []


def test_missing_confidence_defaulted():
    """Test 2: normalize_output with missing confidence returns confidence=None, normalized_fields=['confidence']."""
    raw = json.dumps({
        "answer": "Something happened.",
        "sources": [],
        "latency_ms": 50,
    })
    result = normalize_output(raw, duration_ms=80)
    assert result.confidence is None
    assert "confidence" in result.normalized_fields


def test_missing_sources_defaulted():
    """Test 3: normalize_output with missing sources returns sources=[], normalized_fields=['sources']."""
    raw = json.dumps({
        "answer": "Short answer.",
        "confidence": 0.8,
        "latency_ms": 30,
    })
    result = normalize_output(raw, duration_ms=40)
    assert result.sources == []
    assert "sources" in result.normalized_fields


def test_plain_string_answer():
    """Test 4: normalize_output with plain string (no JSON envelope) wraps entire text as answer."""
    raw = "This is a plain text answer."
    result = normalize_output(raw, duration_ms=200)
    assert result.answer == "This is a plain text answer."
    assert result.sources == []
    assert result.confidence is None
    assert result.latency_ms == 200  # defaults to duration_ms
    assert "sources" in result.normalized_fields
    assert "confidence" in result.normalized_fields
    assert "latency_ms" in result.normalized_fields


def test_json_without_answer_key():
    """Test 5: normalize_output with JSON but no 'answer' key treats entire text as plain string."""
    raw = json.dumps({"result": "something", "status": "ok"})
    result = normalize_output(raw, duration_ms=100)
    assert "result" in result.answer or raw in result.answer  # whole raw becomes answer
    assert result.sources == []


def test_source_object_fields():
    """Test 6: Source objects have url, title, snippet, page fields (all optional)."""
    s = Source()
    assert s.url is None
    assert s.title is None
    assert s.snippet is None
    assert s.page is None

    s2 = Source(url="https://example.com", title="Test", snippet="A snippet", page=3)
    assert s2.url == "https://example.com"
    assert s2.page == 3


def test_latency_ms_from_json_takes_priority():
    """Test 7: If latency_ms is in JSON, it takes priority over duration_ms param."""
    raw = json.dumps({
        "answer": "Test answer.",
        "sources": [],
        "confidence": 0.9,
        "latency_ms": 75,
    })
    result = normalize_output(raw, duration_ms=999)
    assert result.latency_ms == 75
    assert "latency_ms" not in result.normalized_fields


def test_missing_latency_uses_duration_ms():
    """Test 8: If latency_ms is missing from JSON, duration_ms parameter is used."""
    raw = json.dumps({
        "answer": "Another answer.",
        "sources": [],
        "confidence": 0.7,
    })
    result = normalize_output(raw, duration_ms=333)
    assert result.latency_ms == 333
    assert "latency_ms" in result.normalized_fields


def test_normalized_envelope_is_pydantic_model():
    """Test 9: NormalizedEnvelope is a Pydantic model with correct fields."""
    env = NormalizedEnvelope(
        answer="Hello",
        sources=[Source(url="https://x.com")],
        confidence=0.5,
        latency_ms=100,
        normalized_fields=["foo"],
    )
    assert env.answer == "Hello"
    assert env.confidence == 0.5
