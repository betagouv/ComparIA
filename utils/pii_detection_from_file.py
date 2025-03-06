import csv
import psycopg2
import os
from urllib.parse import urlparse


def mark_sensitive_conversations(csv_file):

    dsn = os.getenv("DATABASE_URI")
    if not dsn:
        print("Error: DATABASE_URI environment variable not set.")
        return

    try:
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()

        # Collect conversation IDs and their sensitive status
        conversation_data = {}  # {conv_id: {'sensitive': bool, 'questions': set()}}

        with open(csv_file, "r", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                question_id = row["question_id"]
                conversation_ids = question_id.split("-")[:2]
                conversations_pair_id = "-".join(conversation_ids)
                if len(conversation_ids) == 2:
                    is_sensitive = row["contains_sensitive_info"].lower() == "true"


                    if conversations_pair_id not in conversation_data:
                        conversation_data[conversations_pair_id] = {
                                "sensitive": False,
                                "questions": set(),
                            }
                        conversation_data[conversations_pair_id]["questions"].add(question_id)
                        if is_sensitive:
                            conversation_data[conversations_pair_id]["sensitive"] = True

                else:
                    print(f"Invalid question_id format: {question_id}")

        # Update the database
        for conversations_pair_id, data in conversation_data.items():
            try:
                cur.execute(
                # print(
                    "UPDATE conversations SET contains_pii = %s, pii_analyzed = TRUE WHERE conversation_pair_id = %s;",
                    (data["sensitive"], conversations_pair_id),
                )
                conn.commit()
                print(
                    f"Updated conversation {conversations_pair_id}: contains_pii={data['sensitive']}"
                )
            except psycopg2.Error as e:
                print(f"Error updating database for conversation {conversations_pair_id}: {e}")
                conn.rollback()

        cur.close()
        conn.close()

    except FileNotFoundError:
        print(f"CSV file not found: {csv_file}")
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# Example usage (replace with your actual CSV file path)
csv_file_path = "./utils/results/final_privacy_analysis_20250217_230107.csv"  # Replace with your CSV file path

mark_sensitive_conversations(csv_file_path)
