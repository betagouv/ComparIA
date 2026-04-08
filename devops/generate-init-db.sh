#!/bin/bash
# Generate init-db.sql by concatenating schema files from utils/schemas/
# This script creates the initialization SQL file used by Docker PostgreSQL

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCHEMAS_DIR="$PROJECT_ROOT/utils/schemas"
MIGRATIONS_DIR="$SCHEMAS_DIR/migrations"
OUTPUT_FILE="$SCRIPT_DIR/data/init-db.sql"

# Exit silently if init-db.sql already exists
if [ -f "$OUTPUT_FILE" ]; then
    exit 0
fi

echo "Generating init-db.sql from schema files..."

# Create output directory if it doesn't exist
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Clear the output file
> "$OUTPUT_FILE"

# Concatenate all base schema files (excluding migrations directory)
echo "Adding base schema files..."
for sql_file in "$SCHEMAS_DIR"/*.sql; do
    if [ -f "$sql_file" ]; then
        filename=$(basename "$sql_file")
        table_name=$(basename "$sql_file" .sql)
        echo "  - $filename"
        echo "-- $(echo $table_name | tr '[:lower:]' '[:upper:]')" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        cat "$sql_file" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
done

# Concatenate all migration files if migrations directory exists
if [ -d "$MIGRATIONS_DIR" ]; then
    echo "Adding migration files..."
    for migration_file in "$MIGRATIONS_DIR"/*.sql; do
        if [ -f "$migration_file" ]; then
            filename=$(basename "$migration_file")
            echo "  - migrations/$filename"
            echo "-- MIGRATION: $filename" >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
            cat "$migration_file" >> "$OUTPUT_FILE"
            echo "" >> "$OUTPUT_FILE"
        fi
    done
fi

echo "Successfully generated: $OUTPUT_FILE"
