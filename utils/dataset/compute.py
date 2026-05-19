"""
Export ComparIA datasets from PostgreSQL to HuggingFace Hub.

This script:
1. Fetches conversations, votes, and reactions from the database
2. Applies transformations (hashing visitor_id, adding model metadata, calculating energy consumption)
3. Filters out PII, archived data, and specific cohorts (Pix, do-not-track)
4. Exports to multiple formats (parquet, jsonl, tsv samples)
5. Uploads to HuggingFace Hub repositories

Usage:
    python export_dataset.py ./exports conversations
    python export_dataset.py --dry-run
    python export_dataset.py ./exports --dry-run
    python export_dataset.py --count # only count db rows that would be exported exported

Required env vars: COMPARIA_DB_URI, HF_PUSH_DATASET_KEY (if not --dry-run)
"""

import json
import logging
import os
from functools import lru_cache

import pandas as pd
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import and_, col

from backend.config import settings
from backend.llms.models import LLMData
from utils.database.models import Comparison
from utils.database.utils import get_db_comparisons_counts, get_db_comparisons_stream
from utils.utils import LLMS_GENERATED_DATA_FILE, read_json

from .export import commit_and_push, export_data
from .models import (
    DatasetComparison,
    DatasetComparisonBaseMetadata,
    DatasetComparisonExtraMetadata,
    Datasets,
)

logger = logging.getLogger("comparia.dataset")


@lru_cache
def get_raw_llms_data() -> dict[str, LLMData]:
    """
    Load the generated models JSON data.
    Used to enrich conversations with model metadata (params count, energy consumption).
    """
    try:
        llms_data = read_json(LLMS_GENERATED_DATA_FILE)
        return {
            k: LLMData.model_validate(v)
            for k, v in llms_data["models"].items()
            if v.get("status") in ("enabled", "archived")
        }
    except FileNotFoundError:
        logger.error(f"Models JSON file not found at: {LLMS_GENERATED_DATA_FILE}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from: {LLMS_GENERATED_DATA_FILE}")
        raise


async def count_dataset_rows(dataset_names: list[Datasets]):
    """Display row counts for each dataset without performing export."""
    try:
        logger.info("Counting rows for each dataset...")
        counts = await get_db_comparisons_counts(
            {
                "comparisons": and_(
                    col(Comparison.archived) == False,
                    col(Comparison.llm_analyzed) == True,
                    col(Comparison.error) == JSONB.NULL,
                    col(Comparison.cohorts).in_((None, "")),
                ),
                "comparisons_raw": col(Comparison.id) != None,
            }
        )

        for dataset_name, count in counts.items():
            logger.info(f"{dataset_name:15} {count:>10,} rows")
    except Exception as e:
        logger.error(f"An error occurred while counting rows.")
        raise


def comparison_to_turns(db_comparison: Comparison) -> list[dict]:
    llms = get_raw_llms_data()
    ctx = {
        "llm_a": llms[db_comparison.llm_id_a],
        "llm_b": llms[db_comparison.llm_id_b],
        "metadata": DatasetComparisonBaseMetadata.model_validate(
            db_comparison
        ).model_dump(),
        "extra_metadata": DatasetComparisonExtraMetadata.model_validate(
            db_comparison
        ).model_dump(),
    }
    comparison = DatasetComparison.model_validate(db_comparison, context=ctx)
    comp_data = comparison.model_dump()
    comp_meta = comp_data.pop("metadata_")
    comp_extra_meta = comp_data.pop("extra_metadata_")
    comp_turns = comp_data.pop("turns_")

    turns = []
    for idx, turn_data in enumerate(comp_turns):
        turn_meta = turn_data.pop("metadata_")
        turns.append(
            {
                **turn_data,
                "turn": idx,
                **comp_data,
                "metadata": {**turn_meta, **comp_meta},
                "extra_metadata": comp_extra_meta,
            }
        )

    return turns


async def build_dataframe() -> pd.DataFrame:
    llms = get_raw_llms_data()
    dataset = pd.DataFrame()
    failed_comparison_ids: list[str] = []

    async for db_comp in get_db_comparisons_stream():
        try:
            turns = comparison_to_turns(db_comp)
            dataset = pd.concat([dataset, pd.DataFrame(turns)])
        except Exception as exc:
            logger.exception(f"Failed to parse Comparison '{db_comp.id}', skipping...")
            failed_comparison_ids.append(str(db_comp.id))

    logger.info("Finished generating dataframe.")

    if failed_comparison_ids:
        logger.error(
            f"{len(failed_comparison_ids)} comparisons could not be properly parsed: \n{"\n".join([f"- '{id_}'" for id_ in failed_comparison_ids])}"
        )

    return dataset


async def process_datasets(
    dataset_names: list[Datasets],
    export_base_path: str,
    dry_run: bool = False,
):
    """
    Process a single dataset: fetch from DB, transform (anonymize, add metadata),
    Export to multiple formats (parquet, jsonl, samples), and push to HF Hub.

    Args:
        dataset_names: Names of the datasets to process
        export_base_path: Local directory for export
        dry_run: If True, skip HuggingFace upload
    """
    logger.info(f"Starting processing datasets…")

    dataset_path = settings.HF_PUSH_DATASET_PATH
    path_parts = dataset_path.split("/", 1) if dataset_path else []
    repo_org = path_parts[0] if len(path_parts) == 2 else None
    repo_base = path_parts[1] if len(path_parts) == 2 else dataset_path

    logger.info(f"Folder defined for dataset: {export_base_path}")
    logger.info(f"Generating dataset dataframe…")

    df = await build_dataframe()

    # Check if data fetching failed
    if df.empty:
        raise Exception(f"Dataframe is empty, aborting export")

    for dataset_name in dataset_names:
        logger.info(f"Generating '{dataset_name}'…")
        data = df[~df["excluded"]] if dataset_name == "comparisons" else df

        if dataset_name == "comparisons":
            data = df.drop(columns=["excluded", "extra_metadata"])

        repo_name = f"{repo_base}-{dataset_name}"
        repo_path = os.path.join(export_base_path, repo_name)
        # Export data to local files
        export_data(data, dataset_name, repo_path)

        # Upload to HuggingFace Hub (skip if dry_run)
        if dry_run:
            logger.info(f"[DRY RUN] Skipping HuggingFace upload for '{dataset_name}'")
        else:
            commit_and_push(repo_org, repo_name, repo_path)
