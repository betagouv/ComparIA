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

import hashlib
import logging
import os
from functools import lru_cache

import pandas as pd
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import and_, col

from backend.config import settings
from backend.llms.utils import get_active_params, get_total_params
from utils.database.models import Comparison
from utils.database.utils import get_db_comparisons_counts, get_db_comparisons_stream
from utils.utils import db_connection

from .export import commit_and_push, export_data
from .models import (
    DatasetComparison,
    DatasetComparisonBaseMetadata,
    DatasetComparisonExtraMetadata,
    Datasets,
)
from .queries import get_llms_data

# TODO: apply add token ecologits + topics pii + ip_map just before export

logger = logging.getLogger("comparia.dataset")

COMPARIA_DB_URI = settings.COMPARIA_DB_URI


@lru_cache
def get_session_hash_to_ip_map():
    """Load session hash to IP map from database for visitor_id fallback."""
    try:
        with db_connection(stream=True) as conn:
            df = pd.read_sql_query(
                "SELECT ip_map, session_hash FROM conversations", conn
            )
            # Convert DataFrame to dictionary for efficient lookup when visitor_id is missing
            return dict(zip(df["session_hash"], df["ip_map"]))
        return True

    except Exception as e:
        logger.error(f"Failed to load session hash IP mapping: {e}")
        return False


def hash_md5(value):
    """Hash a value using MD5 for anonymization."""
    if not value:
        return None
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def calculate_kwh(model_name, tokens):
    """
    Calculate energy consumption in kWh for a model based on token output.
    Formula: (wh_per_million_token / 1M) * tokens / 1000 = kWh
    """
    llm_data = get_llms_data().get(model_name)

    if tokens is None or not llm_data:
        # FIXME llm can be disabled and therefore excluded from get_llms_data
        return None

    return (llm_data.wh_per_million_token / 1_000_000) * tokens / 1_000


def fetch_and_transform_data(conn, table_name, query=None):
    """
    Fetch data from a database table and apply transformations.

    Transformations include:
    - Hash visitor_id with MD5 for anonymization
    - Fallback to hashed IP map when visitor_id is missing
    - Add model metadata (params count, energy consumption) for conversations
    - Drop sensitive/internal columns (IP, PII flags, cohorts, etc.)
    """

    try:
        logger.info(f"Fetching data for table: {table_name}")

        # Execute SQL query and load all results into a pandas DataFrame
        dataframe = pd.read_sql_query(query, conn)
        logger.info(f"Retrieved {len(dataframe):,} rows for {table_name}")

        if dataframe.empty:
            logger.warning("DataFrame vide - no data to export")
            return dataframe

        # Anonymize visitor_id using MD5 hash
        if "visitor_id" in dataframe.columns:
            logger.info("Hashing visitor_id with MD5...")
            dataframe["visitor_id"] = dataframe["visitor_id"].apply(
                lambda x: hash_md5(x) if pd.notnull(x) else None
            )
            # Fallback: use hashed IP map for rows without visitor_id
            logger.info("Replacing missing visitor_id with hashed IP map ID...")
            session_hash_to_ip_map = get_session_hash_to_ip_map()
            dataframe["visitor_id"] = dataframe.apply(
                lambda row: (
                    hash_md5(f"ip-{session_hash_to_ip_map.get(row['session_hash'])}")
                    if pd.isnull(row["visitor_id"])
                    and session_hash_to_ip_map.get(row["session_hash"])
                    else row["visitor_id"]
                ),
                axis=1,
            )

        # Add model metadata for conversations dataset
        if table_name == "conversations":
            logger.info("Adding model infos...")
            llms_data = get_llms_data()

            # Add parameter counts (total and active) - only for models that exist in MODELS_DATA
            dataframe["model_a_total_params"] = dataframe["model_a_name"].apply(
                lambda x: (
                    get_total_params(llms_data[x.lower()])
                    if x.lower() in llms_data
                    else None
                )
            )
            dataframe["model_b_total_params"] = dataframe["model_b_name"].apply(
                lambda x: (
                    get_total_params(llms_data[x.lower()])
                    if x.lower() in llms_data
                    else None
                )
            )
            dataframe["model_a_active_params"] = dataframe["model_a_name"].apply(
                lambda x: (
                    get_active_params(llms_data[x.lower()])
                    if x.lower() in llms_data
                    else None
                )
            )
            dataframe["model_b_active_params"] = dataframe["model_b_name"].apply(
                lambda x: (
                    get_active_params(llms_data[x.lower()])
                    if x.lower() in llms_data
                    else None
                )
            )

            # Calculate energy consumption with vectorized operations
            dataframe["total_conv_a_kwh"] = None
            dataframe["total_conv_b_kwh"] = None

            for idx, row in dataframe.iterrows():
                dataframe.at[idx, "total_conv_a_kwh"] = calculate_kwh(
                    row["model_a_name"], row["total_conv_a_output_tokens"]
                )
                dataframe.at[idx, "total_conv_b_kwh"] = calculate_kwh(
                    row["model_b_name"], row["total_conv_b_output_tokens"]
                )

        # Drop sensitive columns before export
        # List of sensitive columns :

        columns_to_drop = [
            "archived",
            "pii_analyzed",
            "ip",
            "conversation_a_pii_removed",
            "conversation_b_pii_removed",
            "opening_msg_pii_removed",
            "ip_map",
            "cohorts",
        ]
        dataframe = dataframe.drop(
            columns=[col for col in columns_to_drop if col in dataframe.columns],
            errors="ignore",
        )
        return dataframe

    except Exception as e:
        logger.error(f"Failed to fetch data from {table_name}: {e}")
        # Return None instead of empty DataFrame to indicate failure
        return None


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
    llms = get_llms_data()
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
    llms = get_llms_data()
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
