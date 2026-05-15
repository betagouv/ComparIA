#!/bin/bash
# Generate schema.sql by concatenating schema files from utils/schemas/
# Used by Docker PostgreSQL init via init.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SCHEMAS_DIR="$PROJECT_ROOT/utils/schemas"
MIGRATIONS_DIR="$SCHEMAS_DIR/migrations"
OUTPUT_FILE="$SCRIPT_DIR/schema.sql"

if [ -f "$OUTPUT_FILE" ]; then
    exit 0
fi

echo "Generating schema.sql from schema files..."

> "$OUTPUT_FILE"

# Base schema files only — migrations are for existing DBs and must not be
# re-applied here since the base files already incorporate their changes.
for sql_file in "$SCHEMAS_DIR"/*.sql; do
    if [ -f "$sql_file" ]; then
        table_name=$(basename "$sql_file" .sql)
        echo "  - $(basename "$sql_file")"
        echo "-- $(echo "$table_name" | tr '[:lower:]' '[:upper:]')" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        cat "$sql_file" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
done

echo "Successfully generated: $OUTPUT_FILE"
