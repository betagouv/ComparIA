#!/bin/bash

# Start DuckDB UI with ComparIA local exported datasets

echo "=================================="
echo "Starting DuckDB UI"
echo "=================================="
echo ""
echo "Database: comparia_local.duckdb"
echo "Opening at: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Check if database exists
if [ ! -f "comparia_local.duckdb" ]; then
    echo "⚠️  Database not found! Creating it first..."
    uv run python launch_duckdb_ui.py
fi

# Start DuckDB with UI
duckdb comparia_local.duckdb -init init_ui.sql
