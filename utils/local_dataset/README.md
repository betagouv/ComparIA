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

### 2. Launch the DuckDB CLI

```bash
cd utils/local_dataset
./start_duckdb.sh
```

Or manually:

```bash
# Create the DuckDB database
uv run python load_dataset_duckdb.py
# Launch the CLI
duckdb comparia_local.duckdb
```

## Available tables

- **reactions** - Filtered reactions (without ModelResponseStream, without PII)
- **conversations** - Filtered conversations
- **votes** - User votes

## Useful views

- **reactions_by_model** - Statistics per model
- **reactions_with_comments** - Reactions with user comments
- **check_modelresponsestream** - Legacy ModelResponseStream check

## Data Quality Checks

To verify filtering and data quality (based on dataset/issue.md):

1. Open `verify_dataset.sql` in an editor
2. Copy/paste individual queries into the DuckDB CLI
3. Verify that reactions issues are all 0 (after filtering)
4. Check conversations issues match expected percentages from issue.md

The file contains all checks documented in `dataset/issue.md`:

- msg_index out of bounds
- msg_index not pointing to assistant
- ModelResponseStream in response_content
- ModelResponseStream in JSONB
- Conversations not ending with assistant
- Mismatched conversation pair sizes
- And more...
