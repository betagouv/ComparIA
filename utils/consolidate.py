import psycopg2
import sys
import re

# Function to extract selected_category from the unstructured msg field
def extract_selected_category(msg):
    # Assuming `selected_category` appears like "selected_category: some_category" in the msg
    match = re.search(r"categorie_([^\s,]+)", msg)
    if match:
        return match.group(1)
    return None

# Function to find the relevant log entry by session_hash
def find_selected_category_in_logs(conn, session_hash):
    with conn.cursor() as cur:
        query = """
        SELECT message FROM logs
        WHERE session_hash LIKE %s
        ORDER BY time DESC;
        """
        # Search for the session_hash in the msg field
        cur.execute(query, (f'%{session_hash}%',))
        logs_record = cur.fetchall()
        for log in logs_record:
            msg = log[0]
            print(msg)
            # if extract_selected_category(msg):
                # return extract_selected_category(msg)
            # Extract selected_category from the msg
    return None

# Function to update the PostgreSQL database
def update_selected_category(conn):
    with conn.cursor() as cur:
        # Fetch records where selected_category is NULL
        query = """
        SELECT tstamp, uuid, is_unedited_prompt, selected_category, session_hash
        FROM votes
        WHERE selected_category IS NULL
        ORDER BY tstamp DESC;
        """
        cur.execute(query)
        records = cur.fetchall()

        # Iterate through records
        for record in records:
            tstamp, uuid, is_unedited_prompt, selected_category, session_hash = record
            
            print(f"Looking for session_hash '{session_hash}' in logs...")
            
            # Find the selected_category in the logs database using session_hash
            new_category = find_selected_category_in_logs(conn, session_hash)
            
            if new_category:
                print(f"Found new category: {new_category} for uuid: {uuid}")
                
                # Update the PostgreSQL table with the new selected_category
                update_query = """
                UPDATE votes
                SET selected_category = %s
                WHERE uuid = %s;
                """
                print(update_query)
#                cur.execute(update_query, (new_category, uuid))
                print(f"Updated uuid {uuid} with category {new_category}")
    
    # Commit the changes to the database
    conn.commit()

def get_pg_connection(dsn):
    return psycopg2.connect(dsn)

# Usage example, passing DSN as a command-line argument
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python utils/consolidate.py <dsn>")
        sys.exit(1)

    dsn = sys.argv[1]
    conn = get_pg_connection(dsn)
    
    # Call the function to update the selected_category fields
    update_selected_category(conn)

    conn.close()
