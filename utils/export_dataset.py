import pandas as pd
import logging
import sys
import os
import subprocess
import os
import shutil
import hashlib
from datetime import datetime
import json
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define datasets and their corresponding queries and repository paths
DATASET_CONFIG = {
    "votes": {
        # id	timestamp	model_a_name	model_b_name	model_pair_name	chosen_model_name	opening_msg	both_equal	conversation_a	conversation_b	conv_turns	selected_category	is_unedited_prompt	conversation_pair_id	session_hash	visitor_id	conv_comments_a	conv_comments_b	conv_useful_a	conv_useful_b	conv_creative_a	conv_creative_b	conv_clear_formatting_a	conv_clear_formatting_b	conv_incorrect_a	conv_incorrect_b	conv_superficial_a	conv_superficial_b	conv_instructions_not_followed_a	conv_instructions_not_followed_b	system_prompt_b	system_prompt_a	conv_complete_a	conv_complete_b
        "query": """SELECT v.*
FROM votes v
WHERE v.archived = FALSE
AND EXISTS (
    SELECT 1
    FROM conversations c
    WHERE c.conversation_pair_id = v.conversation_pair_id
    AND c.contains_pii = FALSE
    AND c.pii_analyzed = TRUE
)
;""",
        "repo": "comparia-votes",
    },
    "reactions": {
        "query": """SELECT id, timestamp, model_a_name, model_b_name, refers_to_model, msg_index, opening_msg, conversation_a, conversation_b, model_pos, conv_turns, conversation_pair_id, conv_a_id, conv_b_id, refers_to_conv_id, session_hash, visitor_id, country, city, response_content, question_content, liked, disliked, comment, useful, creative, complete, clear_formatting, incorrect, superficial, instructions_not_followed, model_pair_name, msg_rank, question_id, system_prompt
FROM reactions r
WHERE r.archived = FALSE
AND EXISTS (
    SELECT 1
    FROM conversations c
    WHERE c.conversation_pair_id = r.conversation_pair_id
    AND c.contains_pii = FALSE
    AND c.pii_analyzed = TRUE
)
;""",
        "repo": "comparia-reactions",
    },
    "conversations_raw": {
        "query": """SELECT *
FROM conversations
WHERE archived = FALSE
;""",
        "repo": "comparia-conversations_raw",
    },
    "conversations": {
        "query": """SELECT
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
    country,
    city,
    model_pair_name,
    opening_msg,
    system_prompt_a,
    system_prompt_b,
    selected_category,
    is_unedited_prompt,
    mode,
    custom_models_selection,
    short_summary,
    keywords,
    categories,
    languages,
    total_conv_a_output_tokens,
    total_conv_b_output_tokens,
    model_a_params,
    model_b_params,
    total_conv_a_kwh,
    total_conv_b_kwh,
    ip
FROM conversations
WHERE archived = FALSE
AND pii_analyzed = TRUE
AND contains_pii = FALSE;""",
        "repo": "comparia-conversations",
    },
}

# Global variable to store the IP to number mapping
ip_to_number_mapping = {}


def load_ip_mapping():
    """Loads the IP to number mapping from the database."""
    global ip_to_number_mapping
    DATABASE_URI = os.getenv("DATABASE_URI")
    if not DATABASE_URI:
        logger.error("Cannot connect to the database: no configuration provided")
        return False
    try:
        engine = create_engine(DATABASE_URI)
        with engine.connect() as conn:
            conn.execute(text("INSERT INTO ip_map (ip_address) SELECT DISTINCT ip FROM conversations WHERE ip IS NOT NULL ON CONFLICT (ip_address) DO NOTHING;"))
            conn.commit()

        engine = create_engine(DATABASE_URI, execution_options={"stream_results": True})
        with engine.connect() as conn:
            ip_map = pd.read_sql_query("SELECT * FROM ip_map", conn)
            ip_to_number_mapping = dict(zip(ip_map["ip_address"], (ip_map["id"])))
        logger.info("IP mapping loaded successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to load IP mapping: {e}")
        return False



def load_session_hash_ip():

    global session_hash_to_ip
    DATABASE_URI = os.getenv("DATABASE_URI")
    if not DATABASE_URI:
        logger.error("Cannot connect to the database: no configuration provided")
        return False
    engine = create_engine(DATABASE_URI, execution_options={"stream_results": True})
    with engine.connect() as conn:
        session_hash_to_ip = pd.read_sql_query("SELECT ip, session_hash FROM conversations", conn)
    return True

def session_hash_to_ip_mapping(session_hash):
    ip = session_hash_to_ip.get(session_hash, None)
    return ip_to_number(ip)

def ip_to_number(ip):
    return ip_to_number_mapping.get(ip, None)


def hash_md5(value):
    if not value:
        return None
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def fetch_and_transform_data(conn, table_name, query=None):
    """
    Fetch data from a database table and apply transformations.
    Optionally process visitor_id (hash and fallback to ip_map).
    """

    try:
        logger.info(f"Fetching data for table: {table_name}")
        df = pd.read_sql_query(query, conn)

        if "visitor_id" in df.columns:
            logger.info("Hashing visitor_id with MD5...")
            df["visitor_id"] = df["visitor_id"].apply(
                lambda x: hash_md5(x) if pd.notnull(x) else None
            )
            logger.info("Replacing missing visitor_id with hashed IP map ID...")
            df["visitor_id"] = df.apply(
                lambda row: (
                    hash_md5(f"ip-{session_hash_to_ip_mapping(row['session_hash'])}")
                    if pd.isnull(row["visitor_id"]) and pd.notnull(row["session_hash"])
                    else row["visitor_id"]
                ),
                axis=1,
            )

        columns_to_drop = ["archived", "pii_analyzed", "ip", "chatbot_index", "conversation_a_pii_removed","conversation_b_pii_removed", "opening_msg_pii_removed"]
        
        df = df.drop(
            columns=[col for col in columns_to_drop if col in df.columns],
            errors="ignore",
        )
        for col in ["model_a_params", "model_b_params"]:
            if col in df.columns:
                # df[col] = df[col].apply(lambda x: json.loads(x) if isinstance(x, list) else x)
                df[col] = df[col].apply(lambda x: json.dumps(x))

        return df
    except Exception as e:
        logger.error(f"Failed to fetch data from {table_name}: {e}")
        return pd.DataFrame()


def export_data(df, table_name):
    if df.empty:
        logger.warning(f"No data to export for table: {table_name}")
        return
    export_dir = "datasets"
    if not os.path.exists(export_dir):
        os.makedirs(export_dir, exist_ok=True)
        logger.info(f"Created export directory: {export_dir}")

    logger.info(f"Exporting data for table: {table_name}")
    try:
        df.to_parquet(f"{export_dir}/{table_name}.parquet")
        df.to_json(f"{export_dir}/{table_name}.jsonl", orient="records", lines=True)

        sample_df = df.sample(n=min(len(df), 1000), random_state=42)
        sample_df.to_csv(
            f"{export_dir}/{table_name}_samples.tsv", sep="\t", index=False
        )
        sample_df.to_json(
            f"{export_dir}/{table_name}_samples.jsonl", orient="records", lines=True
        )

        logger.info(f"Export completed for table: {table_name}")
    except Exception as e:
        logger.error(f"Failed to export data for table {table_name}: {e}")


def update_repository(repo_path):
    """Pulls the latest changes for a given repository."""
    if not os.path.exists(repo_path):
        logger.error(f"Repository directory not found: {repo_path}")
        return False
    result = subprocess.run(
        ["git", "-C", repo_path, "pull"], capture_output=True, text=True
    )
    if result.returncode == 0:
        logger.info(f"Successfully pulled latest changes for {repo_path}")
        return True
    else:
        logger.error(f"Failed to pull changes for {repo_path}: {result.stderr}")
        return False


def commit_and_push(repo_path):
    """Commits and pushes changes for a given repository."""
    if not os.path.exists(repo_path):
        logger.error(f"Repository directory not found: {repo_path}")
        return False

    # Check for changes
    status_result = subprocess.run(
        ["git", "-C", repo_path, "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if status_result.returncode != 0:
        logger.error(f"Failed to check status for {repo_path}: {status_result.stderr}")
        return False

    if status_result.stdout.strip():
        # Add all changes
        add_result = subprocess.run(["git", "-C", repo_path, "add", "."])
        if add_result.returncode != 0:
            logger.error(f"Failed to add changes in {repo_path}")
            return False

        # Commit
        commit_message = (
            f"Update data files {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        commit_result = subprocess.run(
            ["git", "-C", repo_path, "commit", "-m", commit_message]
        )
        if commit_result.returncode != 0:
            logger.error(
                f"Failed to commit changes in {repo_path}: {commit_result.stderr}"
            )
            return False

        # Push
        # push_result = subprocess.run(["git", "-C", repo_path, "push", "--dry-run"])
        return True
        # if push_result.returncode == 0:
        #     logger.info(f"Successfully pushed changes for {repo_path}")
        #     return True
        # else:
        #     logger.error(
        #         f"Failed to push changes for {repo_path}: {push_result.stderr}"
        #     )
        #     return False
    else:
        logger.info(f"No changes to commit in {repo_path}")
        return True


def process_dataset(dataset_name, dataset_config):
    """Processes a single dataset."""
    logger.info(f"Starting processing for dataset: {dataset_name}")
    DATABASE_URI = os.getenv("DATABASE_URI")
    if not DATABASE_URI:
        logger.error(
            f"Cannot process {dataset_name}: no database configuration provided"
        )
        return

    repo_name = dataset_config.get("repo")
    query = dataset_config.get("query")

    if not repo_name:
        logger.error(f"No repository defined for dataset: {dataset_name}")
        return

    repo_path = os.path.join("../", repo_name)

    # Pull latest changes for the repository
    if not update_repository(repo_path):
        logger.error(
            f"Failed to update repository for {dataset_name}. Skipping dataset."
        )
        return

    engine = None
    conn = None
    try:
        engine = create_engine(DATABASE_URI, execution_options={"stream_results": True})
        with engine.connect() as conn:
            logger.info(f"Database connection established for dataset: {dataset_name}")

            # Fetch and transform data
            data = fetch_and_transform_data(conn, dataset_name, query)

            # Export data
            export_data(data, dataset_name)

            # Copy exported files to the repository
            dataset_dir = "datasets"
            filename_base = dataset_name
            extensions = [".parquet", ".jsonl", "_samples.tsv", "_samples.jsonl"]
            for ext in extensions:
                filename = filename_base + ext
                src_path = os.path.join(dataset_dir, filename)
                dest_path = os.path.join(os.getcwd(), repo_path, filename)
                if os.path.exists(src_path):
                    try:
                        shutil.copy(src_path, dest_path)
                        logger.info(f"Copied {filename} to {repo_name}")
                    except Exception as e:
                        logger.error(f"Failed to copy {filename} to {repo_name}: {e}")
                else:
                    logger.warning(f"Source file not found: {src_path}")

            # Commit and push changes for the repository
            commit_and_push(repo_path)

    except OperationalError as e:
        logger.error(f"Database connection error for dataset {dataset_name}: {e}")
    except Exception as e:
        logger.error(f"An error occurred while processing dataset {dataset_name}: {e}")
    finally:
        if engine:
            engine.dispose()
            logger.info(f"Database connection closed for dataset: {dataset_name}")


def main():
    if not load_ip_mapping():
        logger.error("Failed to load IP mapping. Exiting.")
        sys.exit(1)

    load_session_hash_ip()

    for dataset_name, config in DATASET_CONFIG.items():
        process_dataset(dataset_name, config)

    logger.info("Finished processing all datasets.")


if __name__ == "__main__":
    main()
