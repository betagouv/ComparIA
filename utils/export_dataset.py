import pandas as pd
import logging
import sys
import os
import subprocess
import os
import shutil
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check database configuration
if not os.getenv("DATABASE_URI"):
    logger.error("Cannot connect to the database: no configuration provided")
    exit(1)


from sqlalchemy import create_engine

DATABASE_URI = os.getenv("DATABASE_URI")

try:
    conn = create_engine(DATABASE_URI, execution_options={"stream_results": True})
    logger.info("Database connection established successfully.")
except Exception as e:
    logger.error(f"Failed to connect to the database: {e}")
    exit(1)


ip_map = pd.read_sql_query("SELECT * FROM ip_map", conn)

ip_to_number_mapping = dict(zip(ip_map["ip_address"], (ip_map["id"])))


def ip_to_number(ip):
    return ip_to_number_mapping.get(ip, None)


import hashlib


def hash_md5(value):
    if not value:
        return None
    return hashlib.md5(value.encode("utf-8")).hexdigest()


# Generic fetch function
def fetch_and_transform_data(table_name, query=None):
    """
    Fetch data from a database table and apply transformations.
    Prioritize visitor_id and fallback to ip_map if no visitor_id.
    """
    query = query or f"SELECT * FROM {table_name} WHERE archived = FALSE"
    try:
        logger.info(f"Fetching data from table: {table_name}")
        df = pd.read_sql_query(query, conn)

        if "visitor_id" in df.columns:
            logger.info("Hashing visitor_id with MD5...")
            df["visitor_id"] = df["visitor_id"].apply(
                lambda x: hash_md5(x) if pd.notnull(x) else None
            )

        # If there are missing visitor_ids, replace them with the MD5 of the ip_map id
        if "visitor_id" in df.columns:
            logger.info("Replacing missing visitor_id with hashed IP map ID...")
            df["visitor_id"] = df.apply(
                lambda row: (
                    hash_md5(f"ip-{ip_to_number(row['ip'])}")
                    if pd.isnull(row["visitor_id"]) and pd.notnull(row["ip"])
                    else row["visitor_id"]
                ),
                axis=1,
            )

        if "archived" in df.columns:
            df = df.drop(columns=["archived"])

        if "pii_analyzed" in df.columns:
            df = df.drop(columns=["pii_analyzed"])

        # TODO: move 'complete' column from reactions dataset after 'clear_formatting'
        # clear_formatting	incorrect
        # if "complete" in df.columns:
        #   old_cols = df.columns.values
        #   new_cols= ['a', 'y', 'b', 'x']
        #   df = df.reindex(columns=new_cols)

        # Unused
        # if "country" in df.columns:
        #     df = df.drop(columns=["country"])
        # if "city" in df.columns:
        #     df = df.drop(columns=["city"])

        if "ip" in df.columns:
            df = df.drop(columns=["ip"])
        if "ip_id" in df.columns:
            df = df.drop(columns=["ip_id"])

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
        os.mkdir(export_dir)
        logger.info(f"Created export directory: {export_dir}")

    logger.info(f"Exporting data for table: {table_name}")
    try:
        df.to_csv(f"{export_dir}/{table_name}.tsv", sep="\t", index=False)
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


def main():
    repos = [
        "comparia-conversations",
        "comparia-reactions",
        "comparia-votes",
        "comparia-conversations_raw",
    ]
    for repo in repos:
        repo_path = os.path.join("../", repo)
        if not os.path.exists(repo_path):
            logger.error(f"Repository directory not found: {repo_path}")
            continue
        result = subprocess.run(
            ["git", "-C", repo_path, "pull"], capture_output=True, text=True
        )
        if result.returncode == 0:
            logger.info(f"Successfully pulled latest changes for {repo}")
        else:
            logger.error(f"Failed to pull changes for {repo}: {result.stderr}")

    # TODO: could use LEFT JOIN
    # LEFT JOIN conversations c ON v.conversation_pair_id = c.conversation_pair_id AND c.contains_pii = TRUE
    # WHERE v.archived = FALSE AND c.conversation_pair_id IS NULL;

    queries = {
        "votes": """SELECT * FROM votes WHERE archived = FALSE AND EXISTS (
SELECT 1
FROM conversations
WHERE conversations.conversation_pair_id = votes.conversation_pair_id
AND contains_pii = FALSE
);
""",
        "reactions": """SELECT * FROM reactions WHERE archived = FALSE AND EXISTS (
SELECT 1
FROM conversations
WHERE conversations.conversation_pair_id = reactions.conversation_pair_id
AND contains_pii = FALSE
);
""",
        "conversations": "SELECT * FROM conversations WHERE archived = FALSE and pii_analyzed = TRUE",
    }

    for table, query in queries.items():
        logger.info(f"Processing table: {table}")

        if table == "conversations":

            logger.info("Processing conversations_raw (no PII scrubbing)...")

            data = fetch_and_transform_data("conversations", query=query)
            export_data(data, "conversations_raw")

            logger.info("Processing conversations with PII scrubbing...")
            conversations_pii_removed = pd.read_sql_query(
                "SELECT * FROM conversations WHERE archived = FALSE and pii_analyzed=TRUE",
                conn,
            )
            conversations_pii_removed["visitor_id"] = conversations_pii_removed[
                "visitor_id"
            ].apply(lambda x: hash_md5(x) if pd.notnull(x) else None)
            conversations_pii_removed["visitor_id"] = conversations_pii_removed.apply(
                lambda row: (
                    hash_md5(f"ip-{ip_to_number(row['ip'])}")
                    if pd.isnull(row["visitor_id"]) and pd.notnull(row["ip"])
                    else row["visitor_id"]
                ),
                axis=1,
            )

            conversations_pii_removed["conversation_a"] = (
                conversations_pii_removed.apply(
                    lambda row: (
                        row["conversation_a_pii_removed"]
                        if row["contains_pii"]
                        else row["conversation_a"]
                    ),
                    axis=1,
                )
            )
            conversations_pii_removed["conversation_b"] = (
                conversations_pii_removed.apply(
                    lambda row: (
                        row["conversation_b_pii_removed"]
                        if row["contains_pii"]
                        else row["conversation_b"]
                    ),
                    axis=1,
                )
            )
            conversations_pii_removed["opening_msg"] = conversations_pii_removed.apply(
                lambda row: (
                    row["opening_msg_pii_removed"]
                    if row["contains_pii"]
                    else row["opening_msg"]
                ),
                axis=1,
            )
            conversations_pii_removed = conversations_pii_removed.drop(
                columns=[
                    "conversation_a_pii_removed",
                    "conversation_b_pii_removed",
                    "opening_msg_pii_removed",
                ]
            )

            conversations_pii_removed.rename(columns={"contains_pii": "pii_removed"})
            if "ip" in conversations_pii_removed.columns:
                conversations_pii_removed = conversations_pii_removed.drop(
                    columns=["ip"]
                )
            if "ip_id" in conversations_pii_removed.columns:
                conversations_pii_removed = conversations_pii_removed.drop(
                    columns=["ip_id"]
                )

            # TODO: refacto in a drop_useless_cols func

            if "archived" in df.columns:
                df = df.drop(columns=["archived"])
                
            if "pii_analyzed" in df.columns:
                df = df.drop(columns=["pii_analyzed"])
                

            export_data(conversations_pii_removed, "conversations")

        else:
            data = fetch_and_transform_data(table, query=query)
            export_data(data, table)

    table_repos = {
        "votes": "../comparia-votes",
        "reactions": "../comparia-reactions",
        "conversations": "../comparia-conversations_raw",
        "conversations_pii_removed": "../comparia-conversations",
    }

    dataset_dir = "datasets"
    if not os.path.exists(dataset_dir):
        logger.error(
            f"Dataset directory {dataset_dir} does not exist. No files to copy."
        )
        return

    # Copy exported files to respective repositories
    for filename in os.listdir(dataset_dir):
        src_path = os.path.join(dataset_dir, filename)
        if not os.path.isfile(src_path):
            continue

        base_name = os.path.splitext(filename)[0]

        main_repo = table_repos.get(base_name)
        destinations = []

        if main_repo is not None:
            destinations.append(main_repo)

            for dest_repo in destinations:
                dest_path = os.path.join(os.getcwd(), dest_repo, filename)
                try:
                    shutil.copy(src_path, dest_path)
                    logger.info(f"Copied {filename} to {dest_repo}")
                except Exception as e:
                    logger.error(f"Failed to copy {filename} to {dest_repo}: {e}")
        else:
            logger.warning(f"No destination repository found for {filename}")

    # Commit and push changes for each repository
    for repo in repos:
        repo_path = os.path.join(os.getcwd(), repo)
        if not os.path.exists(repo_path):
            continue

        # Check for changes
        status_result = subprocess.run(
            ["git", "-C", repo_path, "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        if status_result.returncode != 0:
            logger.error(f"Failed to check status for {repo}: {status_result.stderr}")
            continue

        if status_result.stdout.strip():
            # Add all changes
            add_result = subprocess.run(["git", "-C", repo_path, "add", "."])
            if add_result.returncode != 0:
                logger.error(f"Failed to add changes in {repo}")
                continue

            # Commit
            commit_message = (
                f"Update data files {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            commit_result = subprocess.run(
                ["git", "-C", repo_path, "commit", "-m", commit_message]
            )
            if commit_result.returncode != 0:
                logger.error(
                    f"Failed to commit changes in {repo}: {commit_result.stderr}"
                )
                continue

            # Push
            push_result = subprocess.run(["git", "-C", repo_path, "push", "--dry-run"])
            if push_result.returncode == 0:
                logger.info(f"Successfully pushed changes for {repo}")
            else:
                logger.error(f"Failed to push changes for {repo}: {push_result.stderr}")
        else:
            logger.info(f"No changes to commit in {repo}")


if __name__ == "__main__":
    try:
        main()
    finally:
        conn.dispose()
        logger.info("Database connection closed.")
