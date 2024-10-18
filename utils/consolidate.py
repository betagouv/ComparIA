import os
import json5
import psycopg2
import sys

# Function to read jsonl files and get data by session_hash
# def find_session_in_jsonl(folder_path, session_hash):
#     for filename in os.listdir(folder_path):
#         if filename.endswith('.jsonl'):
#             file_path = os.path.join(folder_path, filename)
#             with open(file_path, 'r') as file:
#                 for line in file:
#                     try:
#                         json_data = json5.loads(line)
#                         if json_data.get("session_hash") == session_hash:
#                             return json_data  # Return first matching JSON
#                     except Exception:
#                         pass
#                         # print(f"Error decoding JSON in file {filename}: {line}")
#     return None

# Function to update the PostgreSQL database
def update_selected_category(folder_path, conn):
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
            
            # Find corresponding json data from jsonl files using session_hash
            print(f"looking for session_hash '{session_hash}'...")
            json_data = find_session_in_jsonl(folder_path, session_hash)
            if json_data:
                print("found json_data:")
                print(json_data)
            if json_data and 'selected_category' in json_data:
                # Extract selected_category from json_data
                new_category = json_data['selected_category']
                
                # Update the PostgreSQL table
                update_query = """
                UPDATE votes
                SET selected_category = %s
                WHERE uuid = %s;
                """
                print(update_query)
                # cur.execute(update_query, (new_category, uuid))
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

    # Define the folder path containing your .jsonl files
    folder_path = "data/s3_prod"


    dsn = sys.argv[1]
    conn = get_pg_connection(dsn)
    
    # Call the function to update the selected_category fields
    update_selected_category(folder_path, conn)

    conn.close()