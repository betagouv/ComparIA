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
import json
import logging
import os
from functools import lru_cache

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from backend.arena.spam_detection import is_spam
from backend.config import PORTAL_DATASET_INFOS, CountryPortal, settings
from backend.llms.utils import get_active_params, get_total_params

from .export import commit_and_push, export_data
from .queries import get_dataset_queries, get_llms_data

# TODO: apply add token ecologits + topics pii + ip_map just before export

logger = logging.getLogger("dataset")

COMPARIA_DB_URI = settings.COMPARIA_DB_URI


@lru_cache
def get_session_hash_to_ip_map():
    """Load session hash to IP map from database for visitor_id fallback."""
    if not COMPARIA_DB_URI:
        logger.error("Cannot connect to the database: no configuration provided")
        return False

    engine = create_engine(COMPARIA_DB_URI, execution_options={"stream_results": True})

    try:
        with engine.connect() as conn:
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


def conversation_contains_spam(conversation_json) -> bool:
    """
    Check if a conversation (JSONB field) contains spam in user messages.

    Args:
        conversation_json: JSON string or parsed list of messages

    Returns:
        True if any user message contains spam, False otherwise
    """
    # Handle null/None values
    if conversation_json is None:
        return False

    # Handle pandas NA/null
    try:
        if pd.isnull(conversation_json):
            return False
    except (ValueError, TypeError):
        # If pd.isnull fails on this value, continue
        pass

    try:
        # Parse JSON if string
        if isinstance(conversation_json, str):
            messages = json.loads(conversation_json)
        else:
            messages = conversation_json

        # Ensure messages is a list
        if not isinstance(messages, list):
            return False

        # Check each user message
        for message in messages:
            if not isinstance(message, dict):
                continue

            if message.get("role") == "user":
                content = message.get("content", "")
                if content and is_spam(str(content)):
                    return True

        return False

    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        logger.debug(f"Failed to parse conversation for spam detection: {e}")
        return False


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

        # Filter out spam conversations (for conversations and reactions tables)
        if (
            table_name in ("conversations", "reactions")
            and "conversation_a" in dataframe.columns
        ):
            logger.info("Filtering spam conversations...")
            initial_count = len(dataframe)

            # Build list of indices to keep (not spam)
            indices_to_keep = []
            for idx, row in dataframe.iterrows():
                has_spam_a = conversation_contains_spam(row["conversation_a"])
                has_spam_b = conversation_contains_spam(row["conversation_b"])

                # Keep row only if neither conversation has spam
                if not has_spam_a and not has_spam_b:
                    indices_to_keep.append(idx)

            # Filter dataframe to keep only non-spam rows
            dataframe = dataframe.loc[indices_to_keep].copy()

            filtered_count = initial_count - len(dataframe)
            if filtered_count > 0:
                logger.info(
                    f"Filtered out {filtered_count:,} spam conversations ({filtered_count/initial_count*100:.1f}%)"
                )
            else:
                logger.info("No spam detected")

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

        # Il faudrait supprimer du dataset ces infos un peu legacy
        # -- FIXME: drop in dataset and keep in database with a note saying it's flaky
        #     -- selected_category VARCHAR(255), (suggested question category)
        #     -- is_unedited_prompt BOOLEAN, (if the prompt is exactly a suggestion)

        # Drop sensitive columns before export
        # List of sensitive columns :

        columns_to_drop = [
            "archived",
            "pii_analyzed",
            "ip",
            "chatbot_index",
            "conversation_a_pii_removed",
            "conversation_b_pii_removed",
            "opening_msg_pii_removed",
            "ip_map",
            "cohorts",
            "country_portal",
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


def count_dataset_rows(country_portal: CountryPortal):
    """Display row counts for each dataset without performing export."""
    if not COMPARIA_DB_URI:
        logger.error("Cannot count rows: no $COMPARIA_DB_URI")
        return False

    engine = None
    try:
        engine = create_engine(COMPARIA_DB_URI)
        with engine.connect() as conn:
            logger.info("Counting rows for each dataset...")
            print("\n" + "=" * 60)
            print("Dataset Row Counts")
            print("=" * 60)

            dataset_queries = get_dataset_queries(country_portal)

            for dataset_name, query in dataset_queries.items():
                if not query:
                    logger.warning(f"No query defined for {dataset_name}")
                    continue

                # Remove trailing semicolon and wrap the original query with COUNT(*)
                clean_query = query.rstrip().rstrip(";")
                count_query = (
                    f"SELECT COUNT(*) as count FROM ({clean_query}) AS subquery"
                )

                try:
                    result = pd.read_sql_query(count_query, conn)
                    count = result["count"].iloc[0]
                    print(f"{dataset_name:30} {count:>10,} rows")
                except Exception as e:
                    logger.error(f"Failed to count rows for {dataset_name}: {e}")
                    print(f"{dataset_name:30} {'ERROR':>10}")

            print("=" * 60 + "\n")
            return True

    except OperationalError as e:
        logger.error(f"Database connection error: {e}")
        return False
    except Exception as e:
        logger.error(f"An error occurred while counting rows: {e}")
        return False
    finally:
        if engine:
            engine.dispose()


def process_dataset(
    dataset_name,
    query,
    country_portal: CountryPortal,
    export_base_path,
    dry_run=False,
):
    """
    Process a single dataset: fetch from DB, transform (anonymize, add metadata),
    Export to multiple formats (parquet, jsonl, samples), and push to HF Hub.

    Args:
        dataset_name: Name of the dataset to process
        dataset_config: Configuration dict with 'query' and 'repo' keys
        export_base_path: Local directory for export
        dry_run: If True, skip HuggingFace upload
    """

    logger.info(f"Starting processing for dataset: {dataset_name}")
    if not COMPARIA_DB_URI:
        logger.error(f"Cannot process {dataset_name}: no $COMPARIA_DB_URI")
        return False

    repo = PORTAL_DATASET_INFOS[country_portal]
    repo_name = f"{repo["name"]}-{dataset_name}"

    logger.info(f"Folder defined for dataset: {export_base_path}")

    repo_path = os.path.join(export_base_path, repo_name)

    engine = None
    conn = None
    try:
        engine = create_engine(
            COMPARIA_DB_URI, execution_options={"stream_results": True}
        )
        with engine.connect() as conn:
            logger.info(f"Database connection established for dataset: {dataset_name}")

            # Fetch and transform data
            data = fetch_and_transform_data(conn, dataset_name, query)

            # Check if data fetching failed
            if data is None:
                logger.error(
                    f"Failed to fetch data for dataset {dataset_name}, aborting export"
                )
                return False

            # Export data to local files
            export_data(data, dataset_name, repo_path)

            # Upload to HuggingFace Hub (skip if dry_run)
            if dry_run:
                logger.info(f"[DRY RUN] Skipping HuggingFace upload for {dataset_name}")
                return True
            else:
                push_success = commit_and_push(
                    repo["org"], repo_name, repo_path, repo["token"]
                )
                return push_success

    except OperationalError as e:
        logger.error(f"Database connection error for dataset {dataset_name}: {e}")
        return False
    except Exception as e:
        logger.error(f"An error occurred while processing dataset {dataset_name}: {e}")
        return False
    finally:
        if engine:
            engine.dispose()
            logger.info(f"Database connection closed for dataset: {dataset_name}")
