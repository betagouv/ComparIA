import os
import traceback
import json
from psycopg2 import sql
import psycopg2
from datetime import datetime

# Database connection parameters
DB_CONNECTION = os.getenv("DB_CONNECTION")

# Directory containing the JSON files
json_directory = "./data/s3_prod"
# json_directory = os.getenv("LOGDIR") or "./data"

# Connect to PostgreSQL

conn = psycopg2.connect(dsn=DB_CONNECTION)
cur = conn.cursor()
print("Successfully connected to the database")

# Create the conversation_logs table if it doesn't exist
cur.execute(
    """
CREATE TABLE IF NOT EXISTS conversation_logs (
    id SERIAL PRIMARY KEY,
    tstamp TIMESTAMP,
    type TEXT,
    conv_id TEXT UNIQUE,
    models TEXT,
    state_a JSONB,
    state_b JSONB,
    model_a_name TEXT,
    model_b_name TEXT,
    ip TEXT,
    details JSONB
);
"""
)

# Loop through each JSON file in the directory
for filename in os.listdir(json_directory):
    if filename.endswith("-conv.json"):
        file_path = os.path.join(json_directory, filename)

        with open(file_path, "r") as file:
            for line in file:
                try:
                    data = json.loads(line)

                    if data.get("type") not in ["slightly-a", "strongly-a", "slightly-b", "strongly-b", "poll"]:
                        if data.get("type") != "chat":
                            print("Ignoring event " + data.get("type"))
                        continue

                    # Prepare SQL INSERT statement
                    insert_query = sql.SQL(
                        """
                    INSERT INTO conversation_logs (tstamp, type, conv_id, models, state_a, state_b, model_a_name, model_b_name, ip, details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s,%s, %s, %s);
                    """
                    )

                    def build_conv_id(data):
                        conv_state = data.get("conversations_state", None)
                        if conv_state:
                            return (
                                conv_state[0].get("conv_id", None)
                                + "-"
                                + conv_state[1].get("conv_id", None)
                            )
                        # elif data.get("state", None):
                        #     return data.get("state", None).get("conv_id", None)
                        else:
                            return None

                    states = data.get("conversations_state", {})
                    # Extract values from JSON
                    tstamp = datetime.fromtimestamp(data.get("tstamp"))
                    type_ = data.get("type")
                    conv_id = build_conv_id(data)
                    models = data.get("models", None)
                    # model = data.get("model", None)
                    state_a = json.dumps(states[0])
                    state_b = json.dumps(states[1])
                    model_a_name = states[0]['model_name']
                    model_b_name = states[1]['model_name']
                    ip = data.get("ip", None)
                    details = json.dumps(data.get(" details", {}))

                    # Execute the insert statement
                    cur.execute(
                        insert_query,
                        (
                            tstamp,
                            type_,
                            conv_id,
                            models,
                            state_a,
                            state_b,
                            model_a_name,
                            model_b_name,
                            ip,
                            details,
                        ),
                    )
                    print("Data successfully parsed")

                except Exception as e:
                    print(f"An error occurred: {e}")
                    pass
                    # print(traceback.format_exc())
                    
        print("Data from " + file_path + " successfully parsed")


# Commit changes and close the connection
conn.commit()
print("All conversation data successfully committed into the database")

# Create the logs table if it doesn't exist
cur.execute(
    """
CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    tstamp TIMESTAMP,
    msg JSONB,
    message TEXT
);
ALTER TABLE logs
ADD UNIQUE (tstamp,message); """
)
conn.commit()

for filename in os.listdir(json_directory):
    if filename.endswith(".jsonl") and filename.startswith("logs-"):
        file_path = os.path.join(json_directory, filename)

        with open(file_path, "r") as file:
            try:
                for line in file:
                    msg = json.loads(line)
                    tstamp = msg.get("time")
                    message = msg.get("message")

                    # Prepare SQL INSERT statement
                    insert_query = sql.SQL(
                        """
                    INSERT INTO logs (tstamp, msg, message)
                    VALUES (%s, %s, %s);
                    """
                    )
                    # print(tstamp)
                    # print(json.dumps(msg))
                    # Execute the insert statement
                    cur.execute(
                        insert_query,
                        (
                            tstamp,
                            json.dumps(msg),
                            message
                        ),
                    )
            except json.decoder.JSONDecodeError:
                # print("Not JSON:" + str(line))
                print("Skipping file " + file_path)
                # print(traceback.format_exc())
                continue
            # except Exception as e:
                # print(f"An error occurred: {e}")
                # print("Line: " + str(line))
                # print(traceback.format_exc())
                # print("Skipping file " + file_path)
        print("Data from " + file_path + " successfully parsed")
    
# Commit changes and close the connection
conn.commit()
print("All data successfully committed into the database")

# finally:
if cur:
    cur.close()
if conn:
    conn.close()
print("Database connection closed")
