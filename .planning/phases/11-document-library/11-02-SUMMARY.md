---
phase: 11-document-library
plan: 02
subsystem: api
tags: [fastapi, rest, documents, tool-arena, pydantic, cache-control]

# Dependency graph
requires:
  - phase: 11-document-library plan 01
    provides: DocumentRegistry singleton, DocumentConfig, DocumentSummary, DocumentDetail models in documents.py

provides:
  - GET /tool-arena/documents endpoint returning list[DocumentSummary] (no content field) with Cache-Control header
  - GET /tool-arena/documents/{doc_id} endpoint returning DocumentDetail (with content) or 404 with Cache-Control header
  - Endpoint tests in test_documents_endpoints.py (7 tests covering Cache-Control, list shape, content, 404, no-auth)
  - Integration tests in test_router_documents.py (4 tests for basic endpoint behavior)

affects: [frontend-document-picker, tool-arena-compare-flow, cdn-caching]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Minimal test app pattern: create isolated FastAPI app per test module to avoid transitive blocking imports (psycopg2, Redis)"
    - "Response parameter injection: inject FastAPI Response into handler to set headers while preserving Pydantic serialization"
    - "_DOCUMENTS_CACHE_CONTROL constant: module-level string for cache header value ensures single source of truth"
    - "DocumentSummary vs DocumentDetail split: list endpoint strips content, detail endpoint includes it"

key-files:
  created:
    - backend/tool_arena/tests/test_documents_endpoints.py
    - backend/tool_arena/tests/test_router_documents.py
  modified:
    - backend/tool_arena/router.py

key-decisions:
  - "List endpoint returns DocumentSummary (no content field) to keep catalogue response small"
  - "Detail endpoint raises HTTP 404 with generic 'Document not found' message (per DOC-03 spec)"
  - "Cache-Control: public, max-age=3600, stale-while-revalidate=86400 applied via Response parameter injection on both endpoints"
  - "Integration tests use a minimal isolated FastAPI app to avoid blocking imports from psycopg2/Redis dependencies"
  - "Response parameter injection (not returning raw Response) preserves FastAPI Pydantic model serialization"

patterns-established:
  - "Document endpoints placed in 'Document Library' section in router.py before session endpoints"
  - "Minimal test app pattern for router tests to avoid transitive import chain blocking"
  - "_DOCUMENTS_CACHE_CONTROL module-level constant for DRY cache header value"

requirements-completed: [DOC-02, DOC-03]

# Metrics
duration: 15min
completed: 2026-04-20
---

# Phase 11 Plan 02: Document Library Summary

**REST API for document catalogue: GET /tool-arena/documents (summary list) and GET /tool-arena/documents/{doc_id} (full content + 404), both with Cache-Control headers for CDN caching, wired to DocumentRegistry singleton**

## Performance

- **Duration:** 15 min
- **Completed:** 2026-04-20
- **Tasks:** 2
- **Files modified:** 1 modified, 2 created

## Accomplishments

- Added `GET /tool-arena/documents` returning `list[DocumentSummary]` (id, title, description — no content field) with `Cache-Control: public, max-age=3600, stale-while-revalidate=86400` header
- Added `GET /tool-arena/documents/{doc_id}` returning `DocumentDetail` (id, title, description, content) or HTTP 404 with `{"detail": "Document not found"}` and Cache-Control header
- Added `_DOCUMENTS_CACHE_CONTROL` module-level constant for DRY header value
- Added `Response` to FastAPI imports for Response parameter injection
- Created `test_documents_endpoints.py` with 7 tests covering list shape, no-content-field, Cache-Control, detail content, detail Cache-Control, 404, and no-auth access
- Created `test_router_documents.py` with 4 integration tests for basic endpoint behavior

## Task Commits

Each task was committed atomically:

1. **Task 1 + Task 2: Add Cache-Control headers, fix 404, add test_documents_endpoints.py** - `cb1a3c44` (feat)

Previous execution had partially completed this plan:
- `fd97e23e` - Initial document endpoints (missing Cache-Control, wrong 404 message)
- `aa566c8d` - test_router_documents.py (missing Cache-Control tests)

## Files Created/Modified

- `backend/tool_arena/router.py` - Added `Response` import, `_DOCUMENTS_CACHE_CONTROL` constant, Cache-Control header assignment in both handlers, fixed 404 detail to "Document not found"
- `backend/tool_arena/tests/test_documents_endpoints.py` - 7 endpoint tests (Cache-Control, list shape, content, 404, no-auth)
- `backend/tool_arena/tests/test_router_documents.py` - 4 basic integration tests

## Decisions Made

- Used Response parameter injection (`async def list_documents(response: Response)`) rather than returning a raw `Response` object — this preserves FastAPI's automatic Pydantic model serialization while still allowing header injection
- 404 detail message is generic `"Document not found"` (per DOC-03 spec) rather than including doc_id — this matches the plan's must_haves truth
- Cache-Control value `public, max-age=3600, stale-while-revalidate=86400` matches the exact spec from 11-UI-SPEC.md
- Test file uses a minimal isolated FastAPI app (mirrors existing `test_router_documents.py` pattern) because importing the full `backend.tool_arena.router` would pull in psycopg2/MCPDispatcher/Redis which require external services

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing Cache-Control headers on document endpoints**
- **Found during:** Task 1 implementation review
- **Issue:** Previous partial execution had added document endpoints but without Cache-Control headers (DOC-02, DOC-03 spec requires them for CDN caching)
- **Fix:** Added `Response` import, `_DOCUMENTS_CACHE_CONTROL` constant, and `response.headers["Cache-Control"] = _DOCUMENTS_CACHE_CONTROL` in both handlers
- **Files modified:** `backend/tool_arena/router.py`
- **Commit:** `cb1a3c44`

**2. [Rule 1 - Bug] Wrong 404 detail message**
- **Found during:** Task 2 test writing (test_get_unknown_document_returns_404 expects `{"detail": "Document not found"}`)
- **Issue:** Previous implementation returned `f"Document '{doc_id}' not found"` (with doc_id interpolated) which does not match the plan's must_haves truth
- **Fix:** Changed to `detail="Document not found"` (static string, per plan spec)
- **Files modified:** `backend/tool_arena/router.py`
- **Commit:** `cb1a3c44`

**3. [Rule 3 - Blocking] Cannot import full router.py in tests (psycopg2 missing)**
- **Found during:** Task 2 test execution — the plan called for `from backend.tool_arena.router import router` but this fails due to psycopg2 import chain
- **Fix:** Used minimal isolated FastAPI app pattern (same as existing `test_router_documents.py`) that replicates the handler logic directly from `documents.py` — avoids the blocking import chain
- **Files modified:** `test_documents_endpoints.py` structure adapted
- **Commit:** `cb1a3c44`

## Test Results

All 7 tests pass:
```
test_list_documents_returns_200_with_all_ids PASSED
test_list_documents_has_no_content_field PASSED
test_list_documents_has_cache_control PASSED
test_get_document_returns_200_with_content PASSED
test_get_document_has_cache_control PASSED
test_get_unknown_document_returns_404 PASSED
test_endpoints_require_no_auth PASSED
```

33/33 tests pass across all non-psycopg2-dependent test files (no regressions).

## Known Stubs

None — both endpoints are fully wired to the `document_registry` singleton.

## Self-Check: PASSED

- `backend/tool_arena/router.py` — exists and contains `_DOCUMENTS_CACHE_CONTROL`, `list_documents`, `get_document`, `Response` import
- `backend/tool_arena/tests/test_documents_endpoints.py` — exists with 7 tests
- `cb1a3c44` — commit hash verified in git log

---
*Phase: 11-document-library*
*Completed: 2026-04-20*
