#!/bin/bash
# Docker PostgreSQL entrypoint init script.
# Creates comparia (via POSTGRES_DB) and comparia_da.
# Schema is applied via Alembic migrations (make db-migrate).

set -e

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -c "CREATE DATABASE comparia_da OWNER \"${POSTGRES_USER}\";"
