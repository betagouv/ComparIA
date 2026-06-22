import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import HfApi

logger = logging.getLogger("comparia.dataset")

# How many rows to buffer before flushing a parquet row group. Caps peak
# memory: we never hold the whole dataset (or a full DataFrame copy) in RAM,
# which is what made the old "accumulate everything then to_parquet" path swap
# on large exports. This is also the parquet row-group size, so don't make it
# tiny.
BATCH_ROWS = 10_000
SAMPLE_SIZE = 1000
SAMPLE_SEED = 42


class StreamingDatasetExporter:
    """
    Write one dataset (parquet + a small sample tsv/jsonl) incrementally.

    Rows are pushed in as they are produced and flushed in batches, so memory
    stays bounded regardless of dataset size. The parquet file is a single
    file written as successive row groups.

    Pass `schema_rows` (fully-populated example rows) to fix the parquet schema
    up front. This matters because the export streams comparisons ordered by
    `created_at`: columns added to the product later (analysis fields,
    `custom_models_selection`, `error`, message `reasoning_content`, …) are all
    null for long stretches of the oldest rows. Inferring the schema from the
    first batch alone would type those columns as null and then fail when a
    later batch populates them. With `schema_rows` the types are known before
    any data is written. If omitted, the schema is inferred from the first batch
    (fine for uniform inputs such as tests).

    We do not emit the full multi-GB `{name}.jsonl`: nothing consumes it (the
    parquet is the canonical format used by HuggingFace and our own tooling),
    it would be ~70% of the published bytes, and serialising it was the export's
    memory and time bottleneck. The tiny sample previews are still written.
    """

    def __init__(
        self,
        dataset_name: str,
        export_dir: Path,
        *,
        keep: Callable[[dict], bool] = lambda row: True,
        drop_columns: tuple[str, ...] = (),
        schema_rows: list[dict] | None = None,
        batch_rows: int = BATCH_ROWS,
    ):
        self.dataset_name = dataset_name
        self.export_dir = export_dir
        self.keep = keep
        self.drop_columns = drop_columns
        self.batch_rows = batch_rows

        export_dir.mkdir(exist_ok=True)
        self._parquet_path = export_dir / f"{dataset_name}.parquet"

        self._buffer: list[dict] = []
        self._parquet_writer: pq.ParquetWriter | None = None
        self._schema: pa.Schema | None = (
            pa.Table.from_pandas(self._frame(schema_rows), preserve_index=False).schema
            if schema_rows
            else None
        )

        # Reservoir sample (deterministic given input order and seed).
        self._reservoir: list[dict] = []
        self._reservoir_seen = 0
        self._rng = random.Random(SAMPLE_SEED)

        self.total_rows = 0

    def add_rows(self, rows: Iterable[dict]) -> None:
        for row in rows:
            if not self.keep(row):
                continue
            self._buffer.append(row)
            self._sample(row)
            self.total_rows += 1
        if len(self._buffer) >= self.batch_rows:
            self._flush()

    def _frame(self, rows: list[dict]) -> pd.DataFrame:
        # Drop columns once per DataFrame rather than rebuilding every row dict.
        df = pd.DataFrame(rows)
        if self.drop_columns:
            df = df.drop(columns=list(self.drop_columns), errors="ignore")
        return df

    def _sample(self, row: dict) -> None:
        self._reservoir_seen += 1
        if len(self._reservoir) < SAMPLE_SIZE:
            self._reservoir.append(row)
        else:
            j = self._rng.randint(0, self._reservoir_seen - 1)
            if j < SAMPLE_SIZE:
                self._reservoir[j] = row

    def _flush(self) -> None:
        if not self._buffer:
            return
        df = self._frame(self._buffer)

        if self._schema is None:
            # No reference schema given: infer from the first batch and reuse it.
            self._schema = pa.Table.from_pandas(df, preserve_index=False).schema
        # Coerce every batch to the fixed schema. A batch that genuinely can't
        # conform raises loudly rather than producing a silently corrupt file.
        table = pa.Table.from_pandas(df, schema=self._schema, preserve_index=False)
        if self._parquet_writer is None:
            self._parquet_writer = pq.ParquetWriter(self._parquet_path, self._schema)
        self._parquet_writer.write_table(table)

        self._buffer.clear()
        logger.debug(f"  '{self.dataset_name}': {self.total_rows:,} rows written")

    def close(self) -> None:
        self._flush()
        if self._parquet_writer is not None:
            self._parquet_writer.close()

        sample_df = self._frame(self._reservoir)
        sample_df.to_csv(
            self.export_dir / f"{self.dataset_name}_samples.tsv", sep="\t", index=False
        )
        sample_df.to_json(
            self.export_dir / f"{self.dataset_name}_samples.jsonl",
            orient="records",
            lines=True,
            date_format="iso",
        )
        logger.info(
            f"Export completed for dataset '{self.dataset_name}' "
            f"({self.total_rows:,} rows, {len(self._reservoir):,} sampled)."
        )


def commit_and_push(repo_org: str, repo_name: str, repo_path: Path):
    """
    Upload exported files to HuggingFace Hub repository.
    Uses HF upload_folder method with timestamped commit message.

    `delete_patterns=["*.jsonl"]` makes each push self-healing: any full
    `*.jsonl` already on the remote (we no longer produce one) is removed in the
    same commit. The `_samples.jsonl` preview is re-uploaded in this same commit,
    so it is kept (uploaded files take precedence over the delete pattern). On a
    fresh repo this is simply a no-op.
    """
    commit_message = f"Update data files {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logger.info(
        f"Uploading '{repo_path}' to HF '{repo_org}/{repo_name}' with commit message: '{commit_message}'"
    )

    try:
        commit_link = HfApi().upload_folder(
            folder_path=str(repo_path),
            repo_id=f"{repo_org}/{repo_name}",
            repo_type="dataset",
            commit_message=commit_message,
            delete_patterns=["*.jsonl"],
        )
        logger.info(
            f"Successfully pushed changes for '{repo_path}', commit: {commit_link}"
        )
    except Exception as exc:
        logger.error(f"Failed to push changes for '{repo_path}'.")
        raise
