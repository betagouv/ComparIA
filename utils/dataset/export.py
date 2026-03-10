import logging
import os
import subprocess
from datetime import datetime

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
    Uses 'hf upload' CLI command with timestamped commit message.
    """
    commit_message = f"Update data files {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    logger.info(
        f"hf upload {repo_org}/{repo_name} {repo_path} --token $HF_PUSH_DATASET_KEY --repo-type dataset --commit-message '{commit_message}'"
    )

    push_result = subprocess.run(
        [
            "hf",
            "upload",
            (repo_org + "/" + repo_name),
            repo_path,
            "--token",
            os.getenv("HF_PUSH_DATASET_KEY", ""),
            "--repo-type",
            "dataset",
            "--commit-message",
            commit_message,
        ]
    )

    if push_result.returncode == 0:
        logger.info(f"Successfully pushed changes for {repo_path}")
        return True
    else:
        logger.error(f"Failed to push changes for {repo_path}: {push_result.stderr}")
        return False
