import os
import json
from psycopg2 import sql
import psycopg2

# Database connection parameters
DB_CONNECTION = os.getenv("DB_CONNECTION")

# Directory containing the JSON files
json_directory = "./data/s3"

# Connect to PostgreSQL
try:
    conn = psycopg2.connect(dsn=DB_CONNECTION)
    cur = conn.cursor()
    print("Successfully connected to the database")

    # Create the conversation_logs table if it doesn't exist
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS conversation_logs (
        id SERIAL PRIMARY KEY,
        tstamp REAL,
        type TEXT,
        model TEXT,
        gen_params JSONB,
        start REAL,
        finish REAL,
        state JSONB,
        ip TEXT,
        details JSONB
    );
    """
    )
    # Loop through each JSON file in the directory
    for filename in os.listdir(json_directory):
        if filename.endswith(".json"):
            file_path = os.path.join(json_directory, filename)

            with open(file_path, "r") as file:
                for line in file:
                    data = json.loads(line)

                    # Prepare SQL INSERT statement
                    insert_query = sql.SQL(
                        """
                    INSERT INTO conversation_logs (tstamp, type, model, gen_params, start, finish, state, ip, details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """
                    )

                    # Extract values from JSON
                    tstamp = data.get("tstamp")
                    type_ = data.get("type")
                    model = data.get("model", None)
                    gen_params = json.dumps(data.get("gen_params", {}))
                    start = data.get("start", None)
                    finish = data.get("finish", None)
                    state = json.dumps(data.get("state", {}))
                    ip = data.get("ip", None)
                    details = json.dumps(data.get("details", {}))

                    # Execute the insert statement
                    cur.execute(
                        insert_query,
                        (
                            tstamp,
                            type_,
                            model,
                            gen_params,
                            start,
                            finish,
                            state,
                            ip,
                            details,
                        ),
                    )
                    print("Data successfully inserted into the database")

    # Commit changes and close the connection
    conn.commit()
    print("All data successfully committed into the database")

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    if cur:
        cur.close()
    if conn:
        conn.close()
    print("Database connection closed")
