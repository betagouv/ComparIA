import psycopg2
import pandas as pd
import logging
import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
from languia.config import db as db_config


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DROPPED_FIELDS = [
#     "chatbot_index",
# ]

# Check database configuration
if not db_config:
    logger.error("Cannot connect to the database: no configuration provided")
    exit(1)

# Establish database connection
try:
    conn = psycopg2.connect(**db_config)
    logger.info("Database connection established successfully.")
except Exception as e:
    logger.error(f"Failed to connect to the database: {e}")
    exit(1)

# Query templates

QUESTIONS_QUERY = "SELECT refresh_matview_questions(); SELECT * FROM matview_questions;"
# QUESTIONS_QUERY = "SELECT * FROM matview_questions;"
# Needs additional priv.
# QUESTIONS_QUERY = "REFRESH MATERIALIZED VIEW matview_questions; SELECT * FROM matview_questions;"

QUESTIONS_ONLY_QUERY = """SELECT q.question_id,
        q.timestamp,
        q.question_content,
        q.conv_turns,
        q.template,
        q.conversation_pair_id,
        q.session_hash,
        q.visitor_id,
        q.ip,
        q.country,
        q.city,
        q.msg_rank
   FROM matview_questions q;"""

ip_map = pd.read_sql_query("SELECT * FROM ip_map", conn)

# Convert ip_map DataFrame to a dictionary for fast lookup
ip_to_number_mapping = dict(zip(ip_map["ip_address"], (ip_map["id"])))


# Function to map IPs to numbers using ip_map
def ip_to_number(ip):
    return ip_to_number_mapping.get(ip, None)  # Return None if IP not in ip_map


import hashlib


def hash_md5(value):
    """
    Compute the MD5 hash of a string and return it as a hex digest.
    """
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

        # Handling visitor_id transformation
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

        # If there's an IP column, drop it
        if "ip" in df.columns:
            df = df.drop(columns=["ip"])
        if "ip_id" in df.columns:
            df = df.drop(columns=["ip_id"])

        return df
    except Exception as e:
        logger.error(f"Failed to fetch data from {table_name}: {e}")
        return pd.DataFrame()  # Return empty DataFrame on failure


# Export function
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
        # Export full dataset
        df.to_csv(f"{export_dir}/{table_name}.tsv", sep="\t", index=False)
        # df.to_json(f"{export_dir}/{table_name}.json", orient="records", indent=2)
        df.to_json(f"{export_dir}/{table_name}.jsonl", orient="records", lines=True)

        # Export sample of 1000 rows
        sample_df = df.sample(n=min(len(df), 1000), random_state=42)
        sample_df.to_csv(
            f"{export_dir}/{table_name}_samples.tsv", sep="\t", index=False
        )
        # sample_df.to_json(f"{export_dir}/{table_name}_samples.json", orient="records", indent=2)
        sample_df.to_json(
            f"{export_dir}/{table_name}_samples.jsonl", orient="records", lines=True
        )

        logger.info(f"Export completed for table: {table_name}")
    except Exception as e:
        logger.error(f"Failed to export data for table {table_name}: {e}")


# Main processing function
def main():
    # Table-specific queries
    queries = {
        "votes": None,
        "reactions": None,  # Default fetch all
        # "conversations": CONV_QUERY,
        "questions": QUESTIONS_QUERY,
        "questions_only": QUESTIONS_ONLY_QUERY,
    }

    for table, query in queries.items():
        logger.info(f"Processing table: {table}")
        data = fetch_and_transform_data(table, query=query)
        export_data(data, table)


# Run the main process
if __name__ == "__main__":
    try:
        main()
    finally:
        conn.close()
        logger.info("Database connection closed.")
