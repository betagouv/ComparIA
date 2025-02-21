import json
import psycopg2
from psycopg2.extras import Json
import os


# Check database configuration
if not os.getenv("DATABASE_URI"):
    print("Cannot connect to the database: no configuration provided")
    exit(1)


db_connection_str = os.getenv("DATABASE_URI")



query = """
UPDATE conversations 
SET short_summary = %s, keywords = %s, categories = %s, languages = %s
WHERE conversation_pair_id = %s;
"""

try:
    # Connect to the database using the connection string
    conn = psycopg2.connect(db_connection_str)
    cur = conn.cursor()

    # Read the JSONL file and insert data
    with open('utils/results-output/results.jsonl', 'r') as file:
        for line in file:
            data = json.loads(line)
            conversation_pair_id = data.pop('conversation_pair_id')
            
            short_summary = data.get('short_summary')
            keywords = data.get('keywords')
            categories = data.get('txt360_categories')
            languages = data.get('languages')
            
            # Insert data
            cur.execute(query, (short_summary, Json(keywords), Json(categories), Json(languages), conversation_pair_id))
            conn.commit()
            print("added topics to id: "+conversation_pair_id)
            print(f"""
                  conversation_pair_id: {conversation_pair_id}
                  short_summary: {short_summary}
                  keywords: {keywords}
                  categories: {categories}
                  languages: {languages}
                  """)

except Exception as e:
    print(f"Error: {e}")
    if conn:
        conn.rollback()

finally:
    # Close the cursor and connection
    if cur:
        cur.close()
    if conn:
        conn.close()