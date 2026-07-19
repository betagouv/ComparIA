# Dataset export

The dataset exporter reads arena comparisons from PostgreSQL, flattens each
comparison into one row per turn, writes Parquet files and small sample
previews, and optionally publishes them to Hugging Face.

## Prerequisites

- Python 3.13 or later and [`uv`](https://docs.astral.sh/uv/)
- A migrated ComparIA PostgreSQL database containing comparison data
- The data dependency group, installed with `uv sync --group data`
- `COMPARIA_DB_URI`, for example
  `postgresql://comparia:comparia@localhost:5432/comparia`
- `HF_PUSH_DATASET_PATH` in the form `<organisation>/<repository-prefix>`

`HF_PUSH_DATASET_PATH` is required for local exports too: the repository prefix
is used to name output directories and files. `HF_PUSH_DATASET_KEY` is only
required when uploading to Hugging Face.

Settings can be added to the repository's `.env` file or exported in the
current shell. To create and migrate the development database, follow the
[database setup](../../CONTRIBUTING.md#database).

## Export locally

Run commands from the repository root. Use `--dry-run` to write files without
authenticating to or uploading to Hugging Face:

```bash
uv run --group data python comparia-cli generate datasets --dry-run
```

The default exports both dataset variants. Export only one with `--dataset`:

```bash
uv run --group data python comparia-cli generate datasets \
  --dataset normal \
  --dry-run

uv run --group data python comparia-cli generate datasets \
  --dataset raw \
  --dry-run
```

Use `--export-base-path` to write somewhere other than
`utils/local_dataset/`:

```bash
uv run --group data python comparia-cli generate datasets \
  --dry-run \
  --export-base-path /tmp/comparia-datasets
```

Before a full export, row counts can be checked without writing files:

```bash
uv run --group data python comparia-cli generate datasets --count
```

## Dataset variants and output

For `HF_PUSH_DATASET_PATH=example/comparia`, the default output is:

```text
utils/local_dataset/
├── comparia/
│   ├── comparia.parquet
│   ├── comparia_samples.jsonl
│   └── comparia_samples.tsv
└── comparia-raw/
    ├── comparia-raw.parquet
    ├── comparia-raw_samples.jsonl
    └── comparia-raw_samples.tsv
```

The sample files contain at most 1,000 rows. The exporter does not generate a
full JSONL copy; Parquet is the canonical full export.

The variants differ as follows:

| Variant | Contents |
| --- | --- |
| `normal` | Public rows only. Comparisons are excluded when they are archived, not successfully analyzed, marked as PII or spam, associated with an excluded cohort, or contain an error. Internal `excluded` and `extra_metadata` columns are removed. |
| `raw` | All successfully parsed rows, including the `excluded` flag and `extra_metadata`, so filtering decisions can be audited. |

Both variants contain one row per conversation turn. Shared comparison fields
and full conversation histories are repeated on each turn. Writes are streamed
in bounded batches, so the full dataset is not accumulated in memory.

## Reuse an existing raw export

When the raw Parquet already exists under the selected export path, regenerate
only the filtered normal dataset without reading PostgreSQL again:

```bash
uv run --group data python comparia-cli generate datasets \
  --dataset normal \
  --use-cache \
  --dry-run
```

The raw file must be at the path derived from `HF_PUSH_DATASET_PATH`, such as
`utils/local_dataset/comparia-raw/comparia-raw.parquet`. If it is missing, the
command logs a warning and performs a full database export.

## Publish to Hugging Face

Set a token with write access, remove `--dry-run`, and choose the desired
variant:

```bash
export HF_PUSH_DATASET_KEY=hf_...
uv run --group data python comparia-cli generate datasets --dataset normal
```

With `HF_PUSH_DATASET_PATH=example/comparia`, `normal` is uploaded to
`example/comparia` and `raw` to `example/comparia-raw`.

## Verification

The dataset regression tests do not connect to the database, although
`COMPARIA_DB_URI` must be configured because the database engine is initialized
during module imports:

```bash
uv run --group data python tests/dataset/test_comparison_to_turns.py
uv run --group data python tests/dataset/test_streaming_export.py
```

After an export, inspect the Parquet schema and row count with DuckDB:

```bash
uv run --group data python - <<'PY'
import duckdb

path = "utils/local_dataset/comparia/comparia.parquet"
print(duckdb.sql(f"DESCRIBE SELECT * FROM read_parquet('{path}')"))
print(duckdb.sql(f"SELECT count(*) AS rows FROM read_parquet('{path}')"))
PY
```

For command-line options, run:

```bash
uv run --group data python comparia-cli generate datasets --help
```
