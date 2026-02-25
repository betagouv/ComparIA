#!/bin/bash

# Start DuckDB CLI with ComparIA local exported datasets

echo "=================================="
echo "Starting DuckDB CLI"
echo "=================================="
echo ""
echo "Database: comparia_local.duckdb"
echo ""
echo "Press Ctrl+D or type .quit to exit"
echo ""

# Check if database exists
if [ ! -f "comparia_local.duckdb" ]; then
    echo "⚠️  Database not found! Creating it first..."
    uv run python load_dataset_duckdb.py
    echo ""
fi

# Start DuckDB CLI with init script
duckdb comparia_local.duckdb -init init_duckdb.sql
