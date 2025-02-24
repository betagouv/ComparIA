import asyncio
from tqdm import tqdm
import pandas as pd

import logging as logger
import os
import os

CHUNK_SIZE = 50000  # Adjust based on your memory constraints


# Check database configuration
if not os.getenv("DATABASE_URI"):
    logger.error("Cannot connect to the database: no configuration provided")
    exit(1)


from sqlalchemy import create_engine

# Example Database URI (you need to replace with your actual database URI)
DATABASE_URI = os.getenv("DATABASE_URI")

# Create a SQLAlchemy engine

# Establish database connection
try:
    conn = create_engine(DATABASE_URI,execution_options = {'stream_results':True})
    logger.info("Database connection established successfully.")
except Exception as e:
    logger.error(f"Failed to connect to the database: {e}")
    exit(1)
QUESTIONS_QUERY = "SELECT refresh_matview_questions(); SELECT * FROM matview_questions;"
# QUESTIONS_QUERY = "SELECT * FROM matview_questions;"
# Needs additional priv.
# QUESTIONS_QUERY = "REFRESH MATERIALIZED VIEW matview_questions; SELECT * FROM matview_questions;"

# QUESTIONS_ONLY_QUERY = """SELECT q.question_id,
#         q.timestamp,
#         q.question_content,
#         q.conv_turns,
#         q.template,
#         q.conversation_pair_id,
#         q.session_hash,
#         q.visitor_id,
#         q.ip,
#         q.country,
#         q.city,
#         q.msg_rank
#    FROM matview_questions q;"""

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

async def batch_fetch(query, engine, chunk_size=CHUNK_SIZE):
    """Fetch data in batches using server-side cursor"""
    # For materialized view refresh queries, handle separately
    if query and query.lower().startswith('select refresh_matview'):
        queries = query.split(';')
        # Execute refresh
        await asyncio.to_thread(pd.read_sql, queries[0], engine)
        # Use the actual select query for batched fetching
        query = queries[1]

    try:
        total_count = await asyncio.to_thread(
            pd.read_sql,
            f"SELECT COUNT(*) as count FROM ({query}) as sub",
            engine
        )
        total_count = total_count.iloc[0]['count']
    except Exception as e:
        logger.error(f"Error getting total count: {e}")
        return pd.DataFrame()

    with tqdm(total=total_count, desc="Fetching data", unit="rows") as pbar:
        dfs = []
        offset = 0
        
        while True:
            chunk_query = f"""
                SELECT * FROM ({query}) as sub
                LIMIT {chunk_size} OFFSET {offset}
            """
            
            try:
                df_chunk = await asyncio.to_thread(pd.read_sql, chunk_query, engine)
                
                if df_chunk.empty:
                    break
                    
                # Process chunk immediately to free memory
                if "visitor_id" in df_chunk.columns:
                    df_chunk["visitor_id"] = df_chunk["visitor_id"].apply(
                        lambda x: hash_md5(x) if pd.notnull(x) else None
                    )
                    
                    # IP fallback logic
                    df_chunk["visitor_id"] = df_chunk.apply(
                        lambda row: (
                            hash_md5(f"ip-{ip_to_number(row['ip'])}")
                            if pd.isnull(row["visitor_id"]) and pd.notnull(row["ip"])
                            else row["visitor_id"]
                        ),
                        axis=1,
                    )

                # Drop IP columns
                if "ip" in df_chunk.columns:
                    df_chunk = df_chunk.drop(columns=["ip"])
                if "ip_id" in df_chunk.columns:
                    df_chunk = df_chunk.drop(columns=["ip_id"])
                
                dfs.append(df_chunk)
                offset += chunk_size
                pbar.update(len(df_chunk))
                
            except Exception as e:
                logger.error(f"Error fetching chunk at offset {offset}: {e}")
                break

        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

async def process_table(table_name, query=None):
    """Process a single table with batching"""
    query = query or f"SELECT * FROM {table_name} WHERE archived = FALSE"
    return await batch_fetch(query, conn)

async def async_export_data(df, table_name):
    """Async version of export_data"""
    if df.empty:
        logger.warning(f"No data to export for table: {table_name}")
        return
    
    export_dir = "datasets"
    os.makedirs(export_dir, exist_ok=True)

    logger.info(f"Exporting data for table: {table_name}")
    try:
        # Use asyncio.to_thread for potentially blocking IO operations
        await asyncio.gather(
            asyncio.to_thread(df.to_csv, f"{export_dir}/{table_name}.tsv", sep="\t", index=False),
            asyncio.to_thread(df.to_json, f"{export_dir}/{table_name}.jsonl", orient="records", lines=True)
        )

        # Sample export
        sample_df = df.sample(n=min(len(df), 1000), random_state=42)
        await asyncio.gather(
            asyncio.to_thread(sample_df.to_csv, f"{export_dir}/{table_name}_samples.tsv", sep="\t", index=False),
            asyncio.to_thread(sample_df.to_json, f"{export_dir}/{table_name}_samples.jsonl", orient="records", lines=True)
        )

        logger.info(f"Export completed for table: {table_name}")
    except Exception as e:
        logger.error(f"Failed to export data for table {table_name}: {e}")

async def async_main():
    # Process tables
    queries = {
        "votes": None,
        "reactions": None,
        "questions": QUESTIONS_QUERY,
        # "questions_only": QUESTIONS_ONLY_QUERY,
    }

    # Process tables concurrently
    tasks = []
    for table, query in queries.items():
        logger.info(f"Processing table: {table}")
<<<<<<< HEAD
        data = fetch_and_transform_data(table, query=query)
        export_data(data, table)


# Run the main process

    # Define table to repository mappings
    table_repos = {
        'votes': 'comparia-preferences',
        'reactions': 'comparia-preferences',
        'questions': 'comparia-questions',
        # 'questions_only': 'comparia-questions'
    }

    dataset_dir = 'datasets'
    if not os.path.exists(dataset_dir):
        logger.error(f"Dataset directory {dataset_dir} does not exist. No files to copy.")
        return

    # Copy exported files to respective repositories
    for filename in os.listdir(dataset_dir):
        src_path = os.path.join(dataset_dir, filename)
        if not os.path.isfile(src_path):
            continue

        # Determine destination repositories
        if '_samples' in filename:
            base_name = filename.split('_samples')[0]
            is_sample = True
        else:
            base_name = os.path.splitext(filename)[0]
            is_sample = False

        main_repo = table_repos.get(base_name)
        destinations = []

        if main_repo:
            if not is_sample:
                destinations.append(main_repo)
            else:
                destinations.append(main_repo)
                destinations.append('comparia-samples')
        else:
            if is_sample:
                destinations.append('comparia-samples')

        # Copy to each destination
        for dest_repo in destinations:
            dest_path = os.path.join(os.getcwd(), dest_repo, filename)
            try:
                shutil.copy(src_path, dest_path)
                logger.info(f"Copied {filename} to {dest_repo}")
            except Exception as e:
                logger.error(f"Failed to copy {filename} to {dest_repo}: {e}")

    # Commit and push changes for each repository
    for repo in repos:
        repo_path = os.path.join(os.getcwd(), repo)
        if not os.path.exists(repo_path):
            continue

        # Check for changes
        status_result = subprocess.run(['git', '-C', repo_path, 'status', '--porcelain'], capture_output=True, text=True)
        if status_result.returncode != 0:
            logger.error(f"Failed to check status for {repo}: {status_result.stderr}")
            continue

        if status_result.stdout.strip():
            # Add all changes
            add_result = subprocess.run(['git', '-C', repo_path, 'add', '.'])
            if add_result.returncode != 0:
                logger.error(f"Failed to add changes in {repo}")
                continue

            # Commit
            commit_message = f"Update data files {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            commit_result = subprocess.run(['git', '-C', repo_path, 'commit', '-m', commit_message])
            if commit_result.returncode != 0:
                logger.error(f"Failed to commit changes in {repo}: {commit_result.stderr}")
                continue

            # Push
            push_result = subprocess.run(['git', '-C', repo_path, 'push', '--dry-run'])
            if push_result.returncode == 0:
                logger.info(f"Successfully pushed changes for {repo}")
            else:
                logger.error(f"Failed to push changes for {repo}: {push_result.stderr}")
        else:
            logger.info(f"No changes to commit in {repo}")
=======
        df = await process_table(table, query)
        tasks.append(async_export_data(df, table))
    
    # Wait for all exports to complete
    await asyncio.gather(*tasks)
>>>>>>> async-export-dataset


if __name__ == "__main__":
    # try:
    asyncio.run(async_main())
    # finally:
    #     conn.close()
    #     logger.info("Database connection closed.")
