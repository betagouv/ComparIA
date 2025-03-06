import json
import vertexai
from vertexai.generative_models import GenerativeModel
import time
import os
import psycopg2
import csv
from typing import Optional


class Config:
    PROJECT_ID = "languia-430909"
    LOCATION = "europe-west1"
    MODEL_NAME = "gemini-2.0-flash"
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    PROMPT_TEMPLATE = (
        "Task: Replace the parts of the text that contains personal, sensitive, or private information with '********'.\n"
        "Original text: {text}\n"
        "Replaced text: "
    )
    CONNECTION_URI = os.getenv("CONNECTION_URI")
    CSV_PATH = "./utils/results/pii_comparia.csv"
    

class Classifier:
    def __init__(self):
        self.model = self._initialize_model()
        self.conversation_cache = {}  # Cache for entire conversations
        self._load_cache_from_csv()

    def _initialize_model(self):
        try:
            vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
            print(f"Model initialized successfully: {Config.MODEL_NAME}")
            return GenerativeModel(Config.MODEL_NAME)
        except Exception as e:
            print(f"Model initialization failed: {str(e)}")
            return None

    def _get_anonymization(self, text: str) -> Optional[str]:
        """Get anonymization from model with retries."""
        prompt = Config.PROMPT_TEMPLATE.format(text=text)
        print(
            f"Starting anonymization for text: {text[:50]}..."
        )  # print first 50 chars of text.

        for attempt in range(Config.MAX_RETRIES):
            try:
                start_time = time.time()
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.7,
                    },
                )
                elapsed = time.time() - start_time
                print(
                    f"Anonymization attempt {attempt + 1} successful. Time taken: {elapsed:.2f} seconds."
                )
                return response.text

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
        print(f"Anonymization failed for text: {text[:50]}...")
        return None

    def _load_cache_from_csv(self):
        try:
            print(f"Loading cache from CSV: {Config.CSV_PATH}")
            with open(Config.CSV_PATH, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    question_id = row["question_id"]
                    text = row["text"]
                    redacted_llm = row["redacted (LLM)"]
                    conversation_pair_id = "-".join(question_id.split("-")[:2])

                    if conversation_pair_id not in self.conversation_cache:
                        self.conversation_cache[conversation_pair_id] = {}
                    self.conversation_cache[conversation_pair_id][text] = redacted_llm
            print(f"Cache loaded successfully. Entries: {len(self.conversation_cache)}")

        except FileNotFoundError:
            print(f"CSV file not found: {Config.CSV_PATH}")
        except Exception as e:
            print(f"Error loading CSV: {e}")

    def process_database_records(self):
        if not Config.CONNECTION_URI:
            print("CONNECTION_URI environment variable not set.")
            return

        try:
            print("Connecting to database...")
            conn = psycopg2.connect(Config.CONNECTION_URI)
            cur = conn.cursor()

            cur.execute(
                """
                SELECT conversation_pair_id, conversation_a, conversation_b
                FROM conversations
                WHERE pii_detected = true AND opening_msg_pii_removed IS NULL;
                """
            )

            rows = cur.fetchall()
            print(f"Found {len(rows)} rows to process.")

            for row in rows:
                conversation_pair_id, conv_a_json, conv_b_json = row
                print(f"Processing ID: {conversation_pair_id}")

                try:
                    conv_a = json.loads(conv_a_json)
                    conv_b = json.loads(conv_b_json)

                    sanitized_conv_a, opening_msg = self.sanitize_conversation(
                        conv_a, True, conversation_pair_id
                    )
                    sanitized_conv_b, _ = self.sanitize_conversation(
                        conv_b, False, conversation_pair_id
                    )

                    self.update_database(
                        conversation_pair_id,
                        json.dumps(sanitized_conv_a),
                        json.dumps(sanitized_conv_b),
                        opening_msg,
                    )

                except json.JSONDecodeError as e:
                    print(f"JSON decode error for ID {conversation_pair_id}: {e}")

        except psycopg2.Error as e:
            print(f"Database error: {e}")
        finally:
            if conn:
                cur.close()
                conn.close()
                print("Database connection closed.")

    def sanitize_conversation(
        self, conversation, get_opening_msg=False, conversation_pair_id=None
    ):
        sanitized_conversation = []
        opening_msg = None
        first_user_message = True

        for message in conversation:
            if message.get("role") == "user":
                text = message.get("content", "")
                if (
                    conversation_pair_id
                    and conversation_pair_id in self.conversation_cache
                    and text in self.conversation_cache[conversation_pair_id]
                ):
                    sanitized_content = self.conversation_cache[conversation_pair_id][
                        text
                    ]
                    print(f"Cache hit for: {text[:30]}...")
                else:
                    sanitized_content = self._get_anonymization(text)

                if sanitized_content is not None:
                    sanitized_conversation.append(
                        {"role": "user", "content": sanitized_content}
                    )
                    if get_opening_msg and first_user_message:
                        opening_msg = sanitized_content
                        first_user_message = False
                else:
                    sanitized_conversation.append(message)
                    if get_opening_msg and first_user_message:
                        opening_msg = message.get("content", "")
                        first_user_message = False
            else:
                sanitized_conversation.append(message)
        return sanitized_conversation, opening_msg

    def update_database(
        self, conversation_pair_id, sanitized_conv_a, sanitized_conv_b, opening_msg
    ):
        """Update the database with the redacted conversations."""
        if not Config.CONNECTION_URI:
            print("CONNECTION_URI environment variable not set.")
            return

        try:
            print(f"Updating database for conversation_pair_id: {conversation_pair_id}")
            conn = psycopg2.connect(Config.CONNECTION_URI)
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE conversations
                SET conversation_a_pii_removed = %s, conversation_b_pii_removed = %s, opening_msg_pii_removed = %s
                WHERE conversation_pair_id = %s;
                """,
                (sanitized_conv_a, sanitized_conv_b, opening_msg, conversation_pair_id),
            )

            conn.commit()
            print(f"Database updated for conversation_pair_id: {conversation_pair_id}")

        except psycopg2.Error as e:
            print(f"Database update failed: {e}")
        finally:
            if conn:
                cur.close()
                conn.close()


def main():
    classifier = Classifier()
    classifier.process_database_records()


if __name__ == "__main__":
    main()
