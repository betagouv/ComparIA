"""
Export ComparIA datasets from PostgreSQL to HuggingFace Hub.

This script:
1. Fetches Comparisons from the database
2. Validate data with Dataset* models
3. Filters out archived, errored, not analyzed and specific cohorts (Pix, do-not-track) for the public dataset
4. Exports to multiple formats (parquet, jsonl, tsv samples)
5. Uploads to HuggingFace Hub repositories

Usage:
    see `./comparia-cli generate datasets --help`

Required env vars: COMPARIA_DB_URI, HF_PUSH_DATASET_KEY (if not --dry-run)
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

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
    Load the generated LLMs JSON data.
    Used to enrich datasets with metadata (params count, energy consumption).
    """
    try:
        llms_data = read_json(LLMS_GENERATED_DATA_FILE)
        return {
            k: LLMData.model_validate(v)
            for k, v in llms_data["models"].items()
            if v.get("status") in ("enabled", "archived")
        }
    except FileNotFoundError:
        logger.error(f"LLMs JSON file not found at: {LLMS_GENERATED_DATA_FILE}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from: {LLMS_GENERATED_DATA_FILE}")
        raise


async def count_dataset_rows(datasets: list[Datasets]):
    """Display row counts for each dataset without performing export."""
    try:
        logger.info("Counting rows for each dataset...")
        counts = await get_db_comparisons_counts(
            {
                "normal": and_(
                    col(Comparison.archived) == False,
                    col(Comparison.llm_analyzed) == True,
                    col(Comparison.error) == JSONB.NULL,
                    col(Comparison.cohorts).in_((None, "")),
                ),
                "raw": col(Comparison.id) != None,
            }
        )

        for dataset, count in counts.items():
            logger.info(f"{dataset:15} {count:>10,} rows")
    except Exception as e:
        logger.error(f"An error occurred while counting rows.")
        raise


def comparison_to_turns(db_comparison: Comparison) -> list[dict]:
    llms = get_raw_llms_data()
    ctx = {
        # .get() tolerates empty/unknown llm_id (legacy comparisons)
        "llm_a": llms.get(db_comparison.llm_id_a),
        "llm_b": llms.get(db_comparison.llm_id_b),
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
    all_turns: list[dict] = []
    failed_comparison_ids: list[str] = []

    n_comparisons = 0
    async for db_comp in get_db_comparisons_stream():
        try:
            turns = comparison_to_turns(db_comp)
            all_turns.extend(turns)
        except Exception as exc:
            logger.exception(f"Failed to parse Comparison '{db_comp.id}', skipping...")
            failed_comparison_ids.append(str(db_comp.id))
        n_comparisons += 1
        if n_comparisons % 10_000 == 0:
            logger.info(f"Progress: {n_comparisons:,} comparisons processed, {len(all_turns):,} turns accumulated.")

    logger.info(
        f"Finished: {n_comparisons:,} comparisons processed, {len(all_turns):,} turns accumulated, {len(failed_comparison_ids):,} skipped (validation error)."
    )

    if failed_comparison_ids:
        logger.error(
            f"{len(failed_comparison_ids)} comparisons could not be properly parsed: \n{"\n".join([f"- '{id_}'" for id_ in failed_comparison_ids])}"
        )

    return pd.DataFrame(all_turns)


def get_repo_infos() -> tuple[str, str]:
    if not settings.HF_PUSH_DATASET_PATH:
        raise Exception("Missing env var 'HF_PUSH_DATASET_PATH'")

    try:
        org, prefix = settings.HF_PUSH_DATASET_PATH.split("/", 1)
        assert org
        assert prefix
        return org, prefix
    except Exception as exc:
        raise Exception(
            "'HF_PUSH_DATASET_PATH' should match the pattern '{organisation}/{repo_prefix}'"
        )


async def process_datasets(
    datasets: list[Datasets],
    export_base_path: Path,
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

    repo_org, repo_prefix = get_repo_infos()

    logger.info(f"Folder defined for dataset: {export_base_path}")
    logger.info(f"Generating dataset dataframe…")

    df = await build_dataframe()

    # Check if data fetching failed
    if df.empty:
        raise Exception(f"Dataframe is empty, aborting export")

    # Log exclusion breakdown before export
    n_total = len(df)
    n_excluded = int(df["excluded"].sum())
    logger.info(f"Dataset breakdown: {n_total:,} total turns, {n_total - n_excluded:,} included (normal), {n_excluded:,} excluded.")

    extra = pd.DataFrame(df["extra_metadata"].tolist())
    for field in ("archived", "llm_analyzed", "cohorts"):
        counts = extra[field].value_counts(dropna=False).to_dict()
        logger.info(f"  [{field}] {counts}")
    logger.info(f"  [error] has_error={extra['error'].notna().sum():,}")

    for dataset in datasets:
        repo_name = repo_prefix + ("-raw" if dataset == "raw" else "")
        logger.info(f"Generating '{repo_name}'…")
        data = df[~df["excluded"]] if dataset == "normal" else df

        if dataset == "normal":
            data = data.drop(columns=["excluded", "extra_metadata"])

        repo_path = export_base_path / repo_name
        # Export data to local files
        export_data(data, repo_name, repo_path)

        # Upload to HuggingFace Hub (skip if dry_run)
        if dry_run:
            logger.info(f"[DRY RUN] Skipping HuggingFace upload for '{repo_name}'")
        else:
            commit_and_push(repo_org, repo_name, repo_path)
