import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from huggingface_hub import HfApi

logger = logging.getLogger("comparia.dataset")

NESTED_COLUMNS = [
    "response_a",
    "response_b",
    "full_conversation_a",
    "full_conversation_b",
    "metadata",
    "extra_metadata",
]


def _serialize_nested(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Serialize nested columns (lists, dicts) to JSON strings for uniform parquet schema."""
    df = dataframe.copy()
    for col in NESTED_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(lambda v: json.dumps(v, default=str) if v is not None else None)
    return df


def export_data(
    dataframe: pd.DataFrame,
    dataset_name: str,
    export_dir: Path,
) -> None:
    """
    Export DataFrame to multiple formats.

    Generates:
    - Full dataset: parquet, jsonl
    - 1000-row sample: tsv, jsonl
    """
    export_dir.mkdir(exist_ok=True)

    logger.info(f"Exporting data for dataset: '{dataset_name}'")
    try:
        serialized = _serialize_nested(dataframe)

        # Full dataset exports
        logger.debug(f"  Writing '{dataset_name}.parquet'...")
        serialized.to_parquet(f"{export_dir}/{dataset_name}.parquet", index=False)

        logger.debug(
            f"  Writing '{dataset_name}.jsonl' (this may take several minutes for large datasets)..."
        )
        chunk_size = 10_000
        with open(f"{export_dir}/{dataset_name}.jsonl", "w") as f:
            for i in range(0, len(serialized), chunk_size):
                chunk = serialized.iloc[i : i + chunk_size]
                chunk_json = chunk.to_json(
                    orient="records", lines=True, date_format="iso"
                )
                f.write(chunk_json)
                if i + chunk_size < len(serialized):
                    f.write("\n")
                if (i // chunk_size) % 10 == 0:
                    logger.debug(
                        f"    Progress: {i+len(chunk):,}/{len(serialized):,} rows"
                    )

        # Sample dataset exports (max 1000 rows)
        logger.debug(f"  Creating sample ({min(len(serialized), 1000)} rows)...")
        sample_df = serialized.sample(n=min(len(serialized), 1000), random_state=42)

        logger.debug(f"  Writing '{dataset_name}_samples.tsv'...")
        sample_df.to_csv(
            f"{export_dir}/{dataset_name}_samples.tsv", sep="\t", index=False
        )

        logger.debug(f"  Writing '{dataset_name}_samples.jsonl'...")
        sample_df.to_json(
            f"{export_dir}/{dataset_name}_samples.jsonl",
            orient="records",
            lines=True,
            date_format="iso",
        )

        logger.info(f"Export completed for dataset: '{dataset_name}'")
    except Exception as exc:
        logger.error(f"Failed to export data for dataset '{dataset_name}'.")
        raise


def commit_and_push(repo_org: str, repo_name: str, repo_path: Path):
    """
    Upload exported files to HuggingFace Hub repository.
    Uses HF upload_folder method with timestamped commit message.
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
        )
        logger.info(
            f"Successfully pushed changes for '{repo_path}', commit: {commit_link}"
        )
    except Exception as exc:
        logger.error(f"Failed to push changes for '{repo_path}'.")
        raise
