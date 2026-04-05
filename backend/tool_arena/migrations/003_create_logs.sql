-- Migration 003: create logs table for Postgres logging handler
CREATE TABLE IF NOT EXISTS logs (
    id          BIGSERIAL PRIMARY KEY,
    time        TEXT,
    level       TEXT,
    message     TEXT,
    query_params JSONB,
    path_params  JSONB,
    session_hash TEXT,
    extra        JSONB
);
