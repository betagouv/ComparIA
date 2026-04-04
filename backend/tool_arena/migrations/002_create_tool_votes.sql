-- Migration: 002_create_tool_votes
-- Tool arena vote persistence
-- Stores blind comparison votes for MCP tool ranking
-- Run manually: psql $COMPARIA_DB_URI -f backend/tool_arena/migrations/002_create_tool_votes.sql

CREATE TABLE IF NOT EXISTS tool_votes (
    id           SERIAL PRIMARY KEY,
    session_hash TEXT NOT NULL,
    tool_a_id    TEXT NOT NULL,
    tool_b_id    TEXT NOT NULL,
    chosen       TEXT NOT NULL CHECK (chosen IN ('a', 'b', 'tie')),
    llm_id       TEXT NOT NULL,
    task         TEXT NOT NULL,
    goal         TEXT NOT NULL,
    timestamp    TEXT NOT NULL
);
