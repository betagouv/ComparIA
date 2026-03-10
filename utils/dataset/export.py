import logging
import os
from datetime import datetime

from huggingface_hub import HfApi

logger = logging.getLogger("dataset")


def export_data(dataframe, table_name, export_dir):
    """
    Export DataFrame to multiple formats.

    Generates:
    - Full dataset: parquet, jsonl
    - 1000-row sample: tsv, jsonl
    """
    os.makedirs(export_dir, exist_ok=True)

    logger.info(f"Exporting data for table: {table_name}")
    try:
        # Full dataset exports
        logger.debug(f"  Writing {table_name}.parquet...")
        dataframe.to_parquet(f"{export_dir}/{table_name}.parquet")

        logger.debug(
            f"  Writing {table_name}.jsonl (this may take several minutes for large datasets)..."
        )
        # Write in chunks to avoid OOM for large datasets
        chunk_size = 10_000
        with open(f"{export_dir}/{table_name}.jsonl", "w") as f:
            for i in range(0, len(dataframe), chunk_size):
                chunk = dataframe.iloc[i : i + chunk_size]
                chunk_json = chunk.to_json(
                    orient="records", lines=True, date_format="iso"
                )
                f.write(chunk_json)
                if i + chunk_size < len(dataframe):
                    f.write("\n")
                if (i // chunk_size) % 10 == 0:
                    logger.debug(
                        f"    Progress: {i+len(chunk):,}/{len(dataframe):,} rows"
                    )

        # Sample dataset exports (max 1000 rows)
        logger.debug(f"  Creating sample ({min(len(dataframe), 1000)} rows)...")
        sample_df = dataframe.sample(n=min(len(dataframe), 1000), random_state=42)

        logger.debug(f"  Writing {table_name}_samples.tsv...")
        sample_df.to_csv(
            f"{export_dir}/{table_name}_samples.tsv", sep="\t", index=False
        )

        logger.debug(f"  Writing {table_name}_samples.jsonl...")
        sample_df.to_json(
            f"{export_dir}/{table_name}_samples.jsonl",
            orient="records",
            lines=True,
            date_format="iso",
        )

        logger.info(f"Export completed for table: {table_name}")
    except Exception as e:
        logger.error(f"Failed to export data for table {table_name}: {e}")
        import traceback

        logger.error(traceback.format_exc())


def commit_and_push(repo_org, repo_name, repo_path):
    """
    Upload exported files to HuggingFace Hub repository.
    Uses HF upload_folder method with timestamped commit message.
    """
    commit_message = f"Update data files {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logger.info(
        f"Uploading {repo_path} to HF {repo_org}/{repo_name} with commit message: '{commit_message}'"
    )

    try:
        commit_link = HfApi().upload_folder(
            folder_path=repo_path,
            repo_id=f"{repo_org}/{repo_name}",
            repo_type="dataset",
            commit_message=commit_message,
        )
        logger.info(
            f"Successfully pushed changes for {repo_path}, commit: {commit_link}"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to push changes for {repo_path}: {e}")
        return False
