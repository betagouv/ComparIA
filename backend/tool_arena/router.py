"""
FastAPI router for the Tool Arena comparison loop.

Provides 4 endpoints:
  POST /tool-arena/session  — create a new session hash
  POST /tool-arena/compare  — dispatch two MCP calls and return blind results
  POST /tool-arena/vote     — record user vote (with guards)
  GET  /tool-arena/reveal   — reveal tool identities after voting

Per D-01: prefix="/tool-arena", tags=["tool-arena"]
Per UX-01: CompareResponse NEVER leaks tool_id, raw_result, server name, or endpoint.
Per D-04: session hash passed via X-Session-Hash header.
Zero imports from backend.arena.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.tool_arena.client import single_mcp_call
from backend.tool_arena.dispatcher import MCPDispatcher
from backend.tool_arena.normalizer import normalize_output
from backend.tool_arena.sanitizer import sanitize_envelope
from utils.storage.redis import REDIS_TOOL_RANKING_KEY, get_redis_client
from backend.tool_arena.models import save_tool_call_to_db, ToolCallRecord
from backend.tool_arena.persistence import ToolVoteRecord, save_tool_vote_to_db
from backend.tool_arena.registry import registry
from backend.tool_arena.session import (
    create_tool_session,
    retrieve_tool_session,
    store_tool_session,
)

logger = logging.getLogger("tool_arena")

router = APIRouter(prefix="/tool-arena", tags=["tool-arena"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class CompareRequest(BaseModel):
    task: str
    goal: str
    document_content: str = ""


class CompareResponse(BaseModel):
    """
    Blind comparison result.
    CRITICAL per UX-01: NO tool_id, NO server name, NO raw_result, NO endpoint.
    """

    session_hash: str
    result_a: str | None   # mediated_result or None on error
    result_b: str | None
    error_a: str | None    # "Tool encountered an error" or None
    error_b: str | None


class ToolVoteBody(BaseModel):
    chosen: Literal["a", "b", "tie"]


class ToolRevealInfo(BaseModel):
    pos: str              # "a" or "b"
    name: str             # MCPServerConfig.name
    description: str      # MCPServerConfig.description
    duration_ms: int      # from MCPToolCall.duration_ms (0 if error)
    error: str | None     # if tool failed


class ToolRevealResponse(BaseModel):
    chosen: str           # "a" | "b" | "tie"
    tool_a: ToolRevealInfo
    tool_b: ToolRevealInfo


class DryRunRequest(BaseModel):
    tool_id: str


class DryRunCheck(BaseModel):
    name: str             # "connectivity" | "envelope_shape" | "sanitization"
    passed: bool
    detail: str | None = None


class DryRunResponse(BaseModel):
    valid: bool
    tool_id: str
    checks: list[DryRunCheck]
    raw_sample: dict | None = None  # normalized envelope if all checks pass


# ---------------------------------------------------------------------------
# Dependency injection helpers
# ---------------------------------------------------------------------------


def get_tool_session_hash(session_hash: str = Header(..., alias="X-Session-Hash")) -> str:
    if not session_hash:
        raise HTTPException(status_code=400, detail="Missing session hash")
    return session_hash


def get_tool_session(session_hash: str = Depends(get_tool_session_hash)) -> dict:
    try:
        return retrieve_tool_session(session_hash)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Helper: build reveal response from session state
# ---------------------------------------------------------------------------


def _build_reveal_response(session: dict, chosen: str) -> ToolRevealResponse:
    from backend.tool_arena.registry import registry

    tool_a = session["tool_a"]
    tool_b = session["tool_b"]
    server_a = registry.get_server(tool_a["tool_id"])
    server_b = registry.get_server(tool_b["tool_id"])
    return ToolRevealResponse(
        chosen=chosen,
        tool_a=ToolRevealInfo(
            pos="a",
            name=server_a.name,
            description=server_a.description,
            duration_ms=tool_a.get("duration_ms", 0),
            error=tool_a.get("error"),
        ),
        tool_b=ToolRevealInfo(
            pos="b",
            name=server_b.name,
            description=server_b.description,
            duration_ms=tool_b.get("duration_ms", 0),
            error=tool_b.get("error"),
        ),
    )


# ---------------------------------------------------------------------------
# Endpoint 0: GET /tool-arena/leaderboard
# ---------------------------------------------------------------------------


@router.get("/leaderboard")
async def get_tool_leaderboard():
    """
    Return current tool rankings from Redis.

    Response shape: {data_timestamp: float|null, tools: [{tool_id, elo, ...}, ...]}
    Returns empty tools list if Redis is unavailable or no data exists yet.
    """
    try:
        client = get_redis_client()
        raw = client.get(REDIS_TOOL_RANKING_KEY)
    except Exception:
        return {"data_timestamp": None, "tools": []}
    if not raw:
        return {"data_timestamp": None, "tools": []}
    data = json.loads(raw)
    rankings = data.get("rankings", {})
    return {
        "data_timestamp": data.get("timestamp"),
        "tools": list(rankings.values()),
    }


# ---------------------------------------------------------------------------
# Endpoint 0b: POST /tool-arena/dry-run
# ---------------------------------------------------------------------------

_DRY_RUN_TASK = "What is this document about?"
_DRY_RUN_GOAL = "Provide a brief summary"
_DRY_RUN_TIMEOUT = 30  # seconds


@router.post("/dry-run", response_model=DryRunResponse)
async def dry_run(body: DryRunRequest) -> DryRunResponse:
    """Validate a registered RAG tool end-to-end with a hardcoded test prompt.

    Runs three checks:
      1. connectivity — real MCP call with 30s timeout
      2. envelope_shape — normalize_output produces non-empty answer
      3. sanitization — sanitize_envelope runs without error (best-effort)

    Returns structured pass/fail with detail for each check.
    """
    # Lookup — 404 if not registered
    try:
        server = registry.get_server(body.tool_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Tool '{body.tool_id}' not found in registry")

    checks: list[DryRunCheck] = []
    raw_text: str | None = None
    duration_ms: int = 0

    # --- Check 1: connectivity ---
    try:
        raw_text, duration_ms = await asyncio.wait_for(
            single_mcp_call(server, _DRY_RUN_TASK, _DRY_RUN_GOAL),
            timeout=_DRY_RUN_TIMEOUT,
        )
        checks.append(DryRunCheck(name="connectivity", passed=True, detail=f"MCP call succeeded in {duration_ms}ms"))
    except asyncio.TimeoutError:
        checks.append(DryRunCheck(name="connectivity", passed=False, detail=f"MCP call timed out after {_DRY_RUN_TIMEOUT}s"))
    except Exception as exc:
        checks.append(DryRunCheck(name="connectivity", passed=False, detail=str(exc)))

    if not checks[0].passed:
        # Skip remaining checks — no output to validate
        checks.append(DryRunCheck(name="envelope_shape", passed=False, detail="Skipped — connectivity failed"))
        checks.append(DryRunCheck(name="sanitization", passed=False, detail="Skipped — connectivity failed"))
        return DryRunResponse(valid=False, tool_id=body.tool_id, checks=checks, raw_sample=None)

    # --- Check 2: envelope_shape ---
    envelope = None
    try:
        envelope = normalize_output(raw_text, duration_ms)
        if not envelope.answer or not envelope.answer.strip():
            checks.append(DryRunCheck(name="envelope_shape", passed=False, detail="Normalized answer is empty"))
            envelope = None
        else:
            checks.append(DryRunCheck(name="envelope_shape", passed=True, detail=f"Answer: {len(envelope.answer)} chars, sources: {len(envelope.sources)}"))
    except Exception as exc:
        checks.append(DryRunCheck(name="envelope_shape", passed=False, detail=f"normalize_output raised: {exc}"))
        envelope = None

    if envelope is None:
        checks.append(DryRunCheck(name="sanitization", passed=False, detail="Skipped — envelope_shape failed"))
        return DryRunResponse(valid=False, tool_id=body.tool_id, checks=checks, raw_sample=None)

    # --- Check 3: sanitization (best-effort, always passes) ---
    try:
        sanitized = sanitize_envelope(envelope, [server])
        stripped_urls = sum(1 for s in sanitized.sources if s.url is None)
        checks.append(DryRunCheck(name="sanitization", passed=True, detail=f"Sanitized {stripped_urls} source URLs"))
        final_envelope = sanitized
    except Exception as exc:
        # Sanitization is best-effort — log but still pass
        logger.warning("dry_run sanitization raised (non-fatal): %s", exc)
        checks.append(DryRunCheck(name="sanitization", passed=True, detail=f"Sanitization skipped (non-fatal): {exc}"))
        final_envelope = envelope

    valid = all(c.passed for c in checks)
    return DryRunResponse(
        valid=valid,
        tool_id=body.tool_id,
        checks=checks,
        raw_sample=final_envelope.model_dump() if valid else None,
    )


# ---------------------------------------------------------------------------
# Endpoint 1: POST /tool-arena/session
# ---------------------------------------------------------------------------


@router.post("/session")
async def create_session():
    """Create a new tool arena session hash (UUID)."""
    session_hash = create_tool_session()
    return {"session_hash": session_hash}


# ---------------------------------------------------------------------------
# Endpoint 2: POST /tool-arena/compare
# ---------------------------------------------------------------------------


@router.post("/compare", response_model=CompareResponse)
async def compare(body: CompareRequest):
    """
    Dispatch two MCP calls concurrently and return blind, sanitized results.

    Per UX-01: response contains ONLY mediated_result (as result_a/result_b).
    tool_id, raw_result, server name, and endpoint are NEVER exposed.
    """
    session_hash = create_tool_session()
    llm_id = settings.TOOL_ARENA_LLM_ID

    dispatcher = MCPDispatcher()
    tool_a, tool_b = await dispatcher.dispatch(
        task=body.task,
        goal=body.goal,
        llm_id=llm_id,
        session_id=session_hash,
        document_content=body.document_content,
    )

    # Persist both tool calls to DB early (don't lose data if user never votes)
    for tc in (tool_a, tool_b):
        try:
            record = ToolCallRecord(**tc.model_dump(mode="json"))
            save_tool_call_to_db(record.model_dump(mode="json"))
        except Exception as exc:
            logger.error("Failed to persist tool_call %s: %s", tc.call_id, exc)

    # Store full state in Redis (tool_id included — never sent to client)
    session_payload = {
        "session_hash": session_hash,
        "task": body.task,
        "goal": body.goal,
        "llm_id": llm_id,
        "voted": False,
        "tool_a": tool_a.model_dump(mode="json"),
        "tool_b": tool_b.model_dump(mode="json"),
    }
    store_tool_session(session_hash, session_payload)

    # Build blind response — per D-13: error becomes generic message
    result_a = tool_a.mediated_result if tool_a.error is None else None
    result_b = tool_b.mediated_result if tool_b.error is None else None
    error_a = "Tool encountered an error" if tool_a.error is not None else None
    error_b = "Tool encountered an error" if tool_b.error is not None else None

    return CompareResponse(
        session_hash=session_hash,
        result_a=result_a,
        result_b=result_b,
        error_a=error_a,
        error_b=error_b,
    )


# ---------------------------------------------------------------------------
# Endpoint 3: POST /tool-arena/vote
# ---------------------------------------------------------------------------


@router.post("/vote", response_model=ToolRevealResponse)
async def vote(
    body: ToolVoteBody,
    session_hash: str = Depends(get_tool_session_hash),
    session: dict = Depends(get_tool_session),
):
    """
    Record user's blind vote and reveal tool identities.

    Guards:
      - 403 if already voted (re-vote prevention, Pitfall 2)
      - 422 if both tools failed (voting not meaningful, Pitfall 6)
    """
    # Guard: re-vote prevention (Pitfall 2)
    if session.get("voted"):
        raise HTTPException(status_code=403, detail="Already voted")

    # Guard: both tools failed (Pitfall 6)
    if session["tool_a"].get("error") and session["tool_b"].get("error"):
        raise HTTPException(status_code=422, detail="Both tools failed, vote not possible")

    # Mark session as voted
    session["voted"] = True
    session["chosen"] = body.chosen
    store_tool_session(session_hash, session)

    # Persist vote to DB
    tool_a = session["tool_a"]
    tool_b = session["tool_b"]
    vote_record = ToolVoteRecord(
        session_hash=session_hash,
        tool_a_id=tool_a["tool_id"],
        tool_b_id=tool_b["tool_id"],
        chosen=body.chosen,
        llm_id=session["llm_id"],
        task=session["task"],
        goal=session["goal"],
        timestamp=datetime.now().isoformat(),
    )
    try:
        save_tool_vote_to_db(vote_record.model_dump(mode="json"))
    except Exception as exc:
        logger.error("Failed to persist tool_vote for session %s: %s", session_hash, exc)

    return _build_reveal_response(session, body.chosen)


# ---------------------------------------------------------------------------
# Endpoint 4: GET /tool-arena/reveal
# ---------------------------------------------------------------------------


@router.get("/reveal", response_model=ToolRevealResponse)
async def reveal(session: dict = Depends(get_tool_session)):
    """
    Return tool identities and vote outcome.

    Guard: 403 if user has not voted yet (Pitfall 3).
    """
    if not session.get("voted"):
        raise HTTPException(status_code=403, detail="Vote required before reveal")

    return _build_reveal_response(session, session["chosen"])
