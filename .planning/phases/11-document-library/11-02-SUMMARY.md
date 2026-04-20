---
phase: 11-document-library
plan: 02
subsystem: api
tags: [fastapi, rest, documents, tool-arena, pydantic]

# Dependency graph
requires:
  - phase: 11-document-library plan 01
    provides: DocumentRegistry singleton, DocumentConfig, DocumentSummary, DocumentDetail models in documents.py

provides:
  - GET /tool-arena/documents endpoint returning list[DocumentSummary] (no content field)
  - GET /tool-arena/documents/{doc_id} endpoint returning DocumentDetail (with content) or 404
  - Integration tests for both endpoints in test_router_documents.py

affects: [frontend-document-picker, tool-arena-compare-flow]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Minimal test app pattern: create isolated FastAPI app per test module to avoid transitive blocking imports (psycopg2, Redis)"
    - "DocumentSummary vs DocumentDetail split: list endpoint strips content, detail endpoint includes it"

key-files:
  created:
    - backend/tool_arena/tests/test_router_documents.py
    - .planning/phases/11-document-library/11-02-PLAN.md
  modified:
    - backend/tool_arena/router.py

key-decisions:
  - "List endpoint returns DocumentSummary (no content field) to keep catalogue response small"
  - "Detail endpoint raises HTTP 404 with doc_id in detail message for debuggable errors"
  - "Integration tests use a minimal isolated FastAPI app to avoid blocking imports from psycopg2/Redis dependencies"

patterns-established:
  - "Document endpoints placed in 'Document Library' section in router.py before session endpoints"
  - "Minimal test app pattern for router tests (mirrors test_health.py convention)"

requirements-completed: []

# Metrics
duration: 8min
completed: 2026-04-20
---

# Phase 11 Plan 02: Document Library Summary

**REST API for document catalogue: GET /tool-arena/documents (summary list) and GET /tool-arena/documents/{doc_id} (full content + 404) wired to DocumentRegistry singleton**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-20T08:32:47Z
- **Completed:** 2026-04-20T08:41:33Z
- **Tasks:** 2
- **Files modified:** 1 modified, 2 created

## Accomplishments
- Added `GET /tool-arena/documents` returning `list[DocumentSummary]` (id, title, description — no content field for lean catalogue browsing)
- Added `GET /tool-arena/documents/{doc_id}` returning `DocumentDetail` (id, title, description, content) or HTTP 404 with informative message
- Added 4 integration tests covering 200/list shape/all entries, 200/content/known id, and 404/unknown id

## Task Commits

Each task was committed atomically:

1. **Task 1: Add document endpoints to router.py** - `fd97e23e` (feat)
2. **Task 2: Write integration tests for document endpoints** - `aa566c8d` (test)

**Plan metadata:** committed as part of Task 2 commit

## Files Created/Modified
- `backend/tool_arena/router.py` - Added document library import block and two GET endpoints
- `backend/tool_arena/tests/test_router_documents.py` - 4 integration tests using minimal FastAPI test app
- `.planning/phases/11-document-library/11-02-PLAN.md` - Plan file created for this execution

## Decisions Made
- Used a minimal isolated FastAPI app for tests (same pattern as `test_health.py`) to avoid transitive blocking imports from psycopg2 and Redis that are pulled in by the full router
- List endpoint deliberately omits content field — `DocumentSummary` model enforces this at the Pydantic layer
- 404 detail message includes the requested doc_id for easy debugging: `"Document '{doc_id}' not found"`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `python3 -c "from backend.tool_arena.router import router"` fails in isolation due to psycopg2 import chain — this is a pre-existing project constraint, not introduced by this plan. Resolved by using minimal test app pattern for verification.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both document endpoints are live and tested
- Frontend document picker can now call `GET /tool-arena/documents` to enumerate available documents and `GET /tool-arena/documents/{doc_id}` to fetch content for a selected document
- No blockers for frontend integration

---
*Phase: 11-document-library*
*Completed: 2026-04-20*
