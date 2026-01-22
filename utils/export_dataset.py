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

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from backend.llms.utils import get_active_params, get_total_params

# Add the parent directory to the Python path to resolve the 'languia' module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# TODO: apply add token ecologits + topics pii + ip_map just before export

MODELS_JSON_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "models", "generated-models.json"
)
MODELS_DATA = {}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


COMPARIA_DB_URI = os.getenv("COMPARIA_DB_URI")

REPO_ORG = os.getenv("REPO_ORG", "ministere-culture")

# Dataset queries - filter out PII, archived data, and specific cohorts
# All queries exclude: archived=TRUE, contains_pii=TRUE, cohorts matching 'pix' or 'do-not-track'
conversations_db_query = """
SELECT
    id,
    timestamp,
    model_a_name,
    model_b_name,
    conversation_a,
    conversation_b,
    conv_turns,
    conversation_pair_id,
    conv_a_id,
    conv_b_id,
    session_hash,
    visitor_id,
    model_pair_name,
    opening_msg,
    system_prompt_a,
    system_prompt_b,
    mode,
    custom_models_selection,
    short_summary,
    keywords,
    categories,
    languages,
    total_conv_a_output_tokens,
    total_conv_b_output_tokens,
    ip
FROM conversations
WHERE archived = FALSE
AND pii_analyzed = TRUE
AND contains_pii = FALSE
AND postprocess_failed = FALSE
AND (COALESCE(cohorts, '') NOT LIKE '%%pix%%')
;
"""

votes_db_query = """
SELECT v.*
FROM votes v
WHERE v.archived = FALSE
AND EXISTS (
    SELECT 1
    FROM conversations c
    WHERE c.conversation_pair_id = v.conversation_pair_id
    AND c.pii_analyzed = TRUE
    AND c.contains_pii = FALSE
    AND c.postprocess_failed = FALSE
    AND (COALESCE(cohorts, '') NOT LIKE '%%pix%%')
)
;
"""

reactions_db_query = """
SELECT id, timestamp, model_a_name, model_b_name, refers_to_model, msg_index, opening_msg, conversation_a, conversation_b, model_pos, conv_turns, conversation_pair_id, conv_a_id, conv_b_id, refers_to_conv_id, session_hash, visitor_id, response_content, question_content, liked, disliked, comment, useful, creative, complete, clear_formatting, incorrect, superficial, instructions_not_followed, model_pair_name, msg_rank, question_id, system_prompt
FROM reactions r
WHERE r.archived = FALSE
AND EXISTS (
    SELECT 1
    FROM conversations c
    WHERE c.conversation_pair_id = r.conversation_pair_id
    AND c.contains_pii = FALSE
    AND c.pii_analyzed = TRUE
    AND c.postprocess_failed = FALSE
    AND (COALESCE(cohorts, '') NOT LIKE '%%pix%%')
)
;
"""

conversations_raw_db_query = """
SELECT *
FROM conversations
WHERE archived = FALSE
;
"""

DATASET_CONFIG = {
    "conversations": {
        "query": conversations_db_query,
        "repo": "comparia-conversations",
    },
    "votes": {
        "query": votes_db_query,
        "repo": "comparia-votes",
    },
    "reactions": {
        "query": reactions_db_query,
        "repo": "comparia-reactions",
    },
    "conversations_raw": {
        "query": conversations_raw_db_query,
        "repo": "comparia-conversations_raw",
    },
}


def load_session_hash_ip():
    """Load session hash to IP map from database for visitor_id fallback."""
    global session_hash_to_ip_map
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
            session_hash_to_ip_map = dict(zip(df["session_hash"], df["ip_map"]))
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
    if tokens is None:
        return None
    wh_per_million = MODELS_DATA.get(model_name.lower(), {}).get(
        "wh_per_million_token", 0
    )
    return (wh_per_million / 1_000_000) * tokens / 1_000


def load_models_data():
    """
    Load the generated models JSON data.
    Used to enrich conversations with model metadata (params count, energy consumption).
    """
    global MODELS_DATA
    try:
        with open(MODELS_JSON_PATH, "r") as f:
            models_data = json.load(f)
            # Access the nested "models" key in the JSON structure
            if "models" in models_data:
                MODELS_DATA = {k.lower(): v for k, v in models_data["models"].items()}
            else:
                MODELS_DATA = {k.lower(): v for k, v in models_data.items()}
    except FileNotFoundError:
        logger.error(f"Models JSON file not found at: {MODELS_JSON_PATH}")
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from: {MODELS_JSON_PATH}")


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
        if dataframe.empty:
            logger.warning("DataFrame vide")

        # Anonymize visitor_id using MD5 hash
        if "visitor_id" in dataframe.columns:
            logger.info("Hashing visitor_id with MD5...")
            dataframe["visitor_id"] = dataframe["visitor_id"].apply(
                lambda x: hash_md5(x) if pd.notnull(x) else None
            )
            # Fallback: use hashed IP map for rows without visitor_id
            logger.info("Replacing missing visitor_id with hashed IP map ID...")
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
            # Add parameter counts (total and active) - only for models that exist in MODELS_DATA
            dataframe["model_a_total_params"] = dataframe["model_a_name"].apply(
                lambda x: (
                    get_total_params(MODELS_DATA.get(x.lower(), {}))
                    if x.lower() in MODELS_DATA
                    else None
                )
            )
            dataframe["model_b_total_params"] = dataframe["model_b_name"].apply(
                lambda x: (
                    get_total_params(MODELS_DATA.get(x.lower(), {}))
                    if x.lower() in MODELS_DATA
                    else None
                )
            )
            dataframe["model_a_active_params"] = dataframe["model_a_name"].apply(
                lambda x: (
                    get_active_params(MODELS_DATA.get(x.lower(), {}))
                    if x.lower() in MODELS_DATA
                    else None
                )
            )
            dataframe["model_b_active_params"] = dataframe["model_b_name"].apply(
                lambda x: (
                    get_active_params(MODELS_DATA.get(x.lower(), {}))
                    if x.lower() in MODELS_DATA
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
        dataframe.to_parquet(f"{export_dir}/{table_name}.parquet")
        dataframe.to_json(
            f"{export_dir}/{table_name}.jsonl", orient="records", lines=True
        )

        # Sample dataset exports (max 1000 rows)
        sample_df = dataframe.sample(n=min(len(dataframe), 1000), random_state=42)
        sample_df.to_csv(
            f"{export_dir}/{table_name}_samples.tsv", sep="\t", index=False
        )
        sample_df.to_json(
            f"{export_dir}/{table_name}_samples.jsonl", orient="records", lines=True
        )

        logger.info(f"Export completed for table: {table_name}")
    except Exception as e:
        logger.error(f"Failed to export data for table {table_name}: {e}")


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


def count_dataset_rows():
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

            for dataset_name, config in DATASET_CONFIG.items():
                query = config.get("query")
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


def process_dataset(dataset_name, dataset_config, repo_prefix, dry_run=False):
    """
    Process a single dataset: fetch from DB, transform (anonymize, add metadata),
    Export to multiple formats (parquet, jsonl, samples), and push to HF Hub.

    Args:
        dataset_name: Name of the dataset to process
        dataset_config: Configuration dict with 'query' and 'repo' keys
        repo_prefix: Local directory for export
        dry_run: If True, skip HuggingFace upload
    """

    logger.info(f"Starting processing for dataset: {dataset_name}")
    if not COMPARIA_DB_URI:
        logger.error(f"Cannot process {dataset_name}: no $COMPARIA_DB_URI")
        return False

    repo_name = dataset_config.get("repo")
    query = dataset_config.get("query")

    if not repo_name:
        logger.error(f"No repository defined for dataset: {dataset_name}")
        return False

    logger.info(f"Folder defined for dataset: {repo_prefix}")

    repo_path = os.path.join(repo_prefix, repo_name)

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
                push_success = commit_and_push(REPO_ORG, repo_name, repo_path)
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


def main():
    """
    Main entry point for dataset export script.

    Args (via command line):
        repo_prefix: directory for export (positional, default: ".")
        dataset: specific dataset to export (positional, optional)
        --dry-run: skip HuggingFace upload (optional)

    Examples:
        python export_dataset.py ./exports conversations
        python export_dataset.py --dry-run
        python export_dataset.py ./exports --dry-run
    """
    parser = argparse.ArgumentParser(
        description="Export ComparIA datasets from PostgreSQL to HuggingFace Hub"
    )
    parser.add_argument(
        "repo_prefix",
        nargs="?",
        type=str,
        default=".",
        help="Directory for local export (default: current directory)",
    )
    parser.add_argument(
        "dataset",
        nargs="?",
        type=str,
        default=None,
        help="Specific dataset to export (conversations, votes, reactions, conversations_raw). Default: all",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip HuggingFace upload (only export locally)",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Display row counts for each dataset without exporting",
    )

    args = parser.parse_args()

    # If --count flag is set, display counts and exit
    if args.count:
        count_dataset_rows()
        return

    # Load lookup tables for data enrichment
    load_session_hash_ip()
    load_models_data()

    # Authenticate with HuggingFace CLI (skip if dry_run)
    if not args.dry_run:
        logger.info("hf auth login --token $HF_PUSH_DATASET_KEY")

        _login_result = subprocess.run(
            args=[
                "hf",
                "auth",
                "login",
                "--token",
                os.getenv("HF_PUSH_DATASET_KEY", ""),
            ]
        )

        if _login_result.returncode == 0:
            logger.info("Logged in")
        else:
            logger.error(f"Failed to login: {_login_result.stderr}")
            return False
    else:
        logger.info("[DRY RUN] Skipping HuggingFace authentication")

    if args.dataset:
        logger.warning(f"only processing dataset: {args.dataset}")

    # Process each dataset (or just the specified one)
    for dataset_name, config in DATASET_CONFIG.items():
        if not args.dataset or args.dataset == dataset_name:
            process_dataset(
                dataset_name, config, args.repo_prefix, dry_run=args.dry_run
            )

    logger.info("Finished processing all datasets.")


if __name__ == "__main__":
    main()
