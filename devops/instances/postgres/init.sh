#!/bin/bash
# Docker PostgreSQL entrypoint init script.
# Creates comparia (via POSTGRES_DB) and comparia_da, applies schema to both.

set -e

SCHEMA=$(sed \
    -e "s/\"languia-dev\"/\"${POSTGRES_USER}\"/g" \
    -e "s/\"languia-prd\"/\"${POSTGRES_USER}\"/g" \
    -e "s/\"languia\"/\"${POSTGRES_USER}\"/g" \
    /tmp/schema.sql)

echo "$SCHEMA" | psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -c "CREATE DATABASE comparia_da OWNER \"${POSTGRES_USER}\";"

echo "$SCHEMA" | psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "comparia_da"
