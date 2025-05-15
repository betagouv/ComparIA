import pandas as pd
import logging
import sys
import os
import subprocess
import os
import shutil
import hashlib
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError


# TODO: apply add token ecologits + topics pii + ip_map just before export

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define datasets and their corresponding queries and repository paths
DATASET_CONFIG = {
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
    model_a_total_params,
    model_a_active_params,
    model_b_active_params,
    model_b_total_params,
    total_conv_a_kwh,
    total_conv_b_kwh,
    ip,
    ip_map
FROM conversations
WHERE archived = FALSE
AND pii_analyzed = TRUE
AND contains_pii = FALSE;""",
# AND postprocess_failed = FALSE
        "repo": "comparia-conversations",
    },
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
}


def load_session_hash_ip():

    global session_hash_to_ip_map
    DATABASE_URI = os.getenv("DATABASE_URI")
    if not DATABASE_URI:
        logger.error("Cannot connect to the database: no configuration provided")
        return False
    engine = create_engine(DATABASE_URI, execution_options={"stream_results": True})
    with engine.connect() as conn:
        session_hash_to_ip_map = pd.read_sql_query("SELECT ip_map, session_hash FROM conversations", conn)
    return True



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
                    hash_md5(f"ip-{session_hash_to_ip_map.get(row['session_hash'])}")
                    if pd.isnull(row["visitor_id"]) and session_hash_to_ip_map.get(row['session_hash'])
                    else row["visitor_id"]
                ),
                axis=1,
            )

        columns_to_drop = ["archived", "pii_analyzed", "ip", "chatbot_index", "conversation_a_pii_removed","conversation_b_pii_removed", "opening_msg_pii_removed", "ip_map"]
        
        df = df.drop(
            columns=[col for col in columns_to_drop if col in df.columns],
            errors="ignore",
        )
        return df
    except Exception as e:
        logger.error(f"Failed to fetch data from {table_name}: {e}")
        return pd.DataFrame()


def export_data(df, table_name, export_dir):
    if df.empty:
        logger.warning(f"No data to export for table: {table_name}")
        return

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


def commit_and_push(repo_org, repo_name, repo_path):
    """Commits and pushes changes for a given repository."""
    # Check for changes
    
        # Commit
    commit_message = (
        f"Update data files {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

# huggingface-cli upload Wauplin/space-example --repo-type=space --exclude="/logs/*" --delete="*" --commit-message="Sync local Space with Hub"
    push_result = subprocess.run(["huggingface-cli", "upload",    (repo_org + "/" + repo_name), repo_path,  "--commit-message", commit_message])

    # push_result = subprocess.run(["git", "pull", "-C", repo_path, "push", "--dry-run"])
    if push_result.returncode == 0:
        logger.info(f"Successfully pushed changes for {repo_path}")
        return True
    else:
        logger.error(
            f"Failed to push changes for {repo_path}: {push_result.stderr}"
        )
        return False


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

    repo_prefix = sys.argv[-1] or "/app/datasets"

    repo_org = os.getenv("REPO_ORG", "https://huggingface.co/datasets/ministere-culture")

    logger.info(f"Folder defined for dataset: {repo_prefix}")

    repo_path = os.path.join(repo_prefix, repo_name)


    # if not os.path.exists(repo_path):
    #     # TODO: refacto
    #     # TODO: use hf-cli upload/download?

    #     logger.info("Cloning into "+ repo_prefix + " from " + repo_org + "/" + repo_name)
    #     _clone_result = subprocess.run(cwd=repo_prefix,
    #                                    args=
    #         ["git", "-C", repo_prefix, "clone", repo_org + "/" + repo_name]
    #     )

    #     if _clone_result.returncode == 0:
    #         logger.info("Cloned")
    #         return True
    #     else:
    #         logger.error(f"Failed to clone for {repo_path}: {_clone_result.stderr}")
    #         return False

    # Pull latest changes for the repository
    # if not update_repository(repo_path):
    #     logger.error(
    #         f"Failed to update repository for {dataset_name}. Skipping dataset."
    #     )
    #     return

    engine = None
    conn = None
    try:
        engine = create_engine(DATABASE_URI, execution_options={"stream_results": True})
        with engine.connect() as conn:
            logger.info(f"Database connection established for dataset: {dataset_name}")

            # Fetch and transform data
            data = fetch_and_transform_data(conn, dataset_name, query)


            # Export data
            export_data(data, dataset_name, repo_path)

            # Commit and push changes for the repository
            commit_and_push(repo_org, repo_name, repo_path)

    except OperationalError as e:
        logger.error(f"Database connection error for dataset {dataset_name}: {e}")
    except Exception as e:
        logger.error(f"An error occurred while processing dataset {dataset_name}: {e}")
    finally:
        if engine:
            engine.dispose()
            logger.info(f"Database connection closed for dataset: {dataset_name}")


def main():

    load_session_hash_ip()
    # logger.info("")
    # subprocess.run(args=
    #         ["git", "--global" "config","credential.helper", "store"]
    #     )
    logger.info("huggingface-cli login --token $HF_TOKEN --add-to-git-credential")

    _login_result = subprocess.run(args=
        ["huggingface-cli","login", "--token", os.getenv("HF_PUSH_DATASET_KEY", ""), "--add-to-git-credential"]
    )
    
    if _login_result.returncode == 0:
        logger.info("Logged in")
    else:
        logger.error(f"Failed to login: {_login_result.stderr}")
        return False
    
    for dataset_name, config in DATASET_CONFIG.items():
        process_dataset(dataset_name, config)

    logger.info("Finished processing all datasets.")


if __name__ == "__main__":
    main()
