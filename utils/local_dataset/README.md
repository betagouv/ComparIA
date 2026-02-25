# Local Dataset Viewer

This folder contains the tools to visualize locally exported datasets with DuckDB.

## Usage

### 1. Export datasets locally

From the `ComparIA/` folder:

```bash
# Export in dry-run mode (without HuggingFace push)
uv run python utils/export_dataset.py --dry-run
# Or export a single dataset
uv run python utils/export_dataset.py --dry-run reactions
```

The `.parquet` files will be created in `utils/local_dataset/comparia-*/`.

### 2. Launch the DuckDB interface

```bash
cd utils/local_dataset
./start_ui.sh
```

Or manually:

```bash
# Create the DuckDB database
uv run python launch_duckdb_ui.py
# Launch the UI
duckdb comparia_local.duckdb -init init_ui.sql
```

The interface will open at http://localhost:3000

## Available tables

- **reactions** - Filtered reactions (without ModelResponseStream, without PII)
- **conversations** - Filtered conversations
- **votes** - User votes

## Useful views

- **reactions_by_model** - Statistics per model
- **check_modelresponsestream** - Filter verification (should be 0 everywhere)
- **reactions_with_comments** - Reactions with user comments

## Checks

To verify that filtering worked correctly:

```sql
-- Should return 0 everywhere
SELECT * FROM check_modelresponsestream;
-- Check stats
SELECT * FROM reactions_by_model LIMIT 10;
```
