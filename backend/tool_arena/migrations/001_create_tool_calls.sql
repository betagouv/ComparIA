-- Migration: 001_create_tool_calls
-- Creates the tool_calls table for CompaRAG Tool Arena
-- Run manually: psql $COMPARIA_DB_URI -f backend/tool_arena/migrations/001_create_tool_calls.sql

CREATE TABLE IF NOT EXISTS tool_calls (
    call_id         TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    task            TEXT NOT NULL,
    goal            TEXT NOT NULL,
    tool_id         TEXT NOT NULL,
    llm_id          TEXT NOT NULL,
    raw_result      TEXT NOT NULL,
    mediated_result TEXT NOT NULL,
    duration_ms     INTEGER NOT NULL,
    created_at      TEXT NOT NULL,
    error           TEXT
);

-- Index for session-based lookups (Phase 3 will query by session)
CREATE INDEX IF NOT EXISTS idx_tool_calls_session_id ON tool_calls (session_id);

-- Index for tool-based analytics (Phase 4 ranking queries)
CREATE INDEX IF NOT EXISTS idx_tool_calls_tool_id ON tool_calls (tool_id);
