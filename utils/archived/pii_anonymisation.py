import json
import vertexai
from vertexai.generative_models import GenerativeModel
import time
import os
import psycopg2
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
    DATABASE_URI = os.getenv("DATABASE_URI")


class Classifier:
    def __init__(self):
        self.needed = 0
        self.error = []
        self.model = self._initialize_model()
        self.anonymization_cache = {}  # Cache to store anonymized texts

    def _initialize_model(self):
        try:
            vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
            print(f"Model initialized successfully: {Config.MODEL_NAME}")
            return GenerativeModel(Config.MODEL_NAME)
        except Exception as e:
            print(f"Model initialization failed: {str(e)}")
            return None

    def _get_anonymization(self, text: str, question_id=None) -> Optional[str]:
        """Get anonymization from model or cache with retries."""
        if text in self.anonymization_cache:
            print(f"Using cached anonymization for text: {text[:50]}...")
            return self.anonymization_cache[text]

        prompt = Config.PROMPT_TEMPLATE.format(text=text)
        print(f"Starting anonymization for text: {text[:50]}...")

        for attempt in range(Config.MAX_RETRIES):
            try:
                start_time = time.time()
                response = self.model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.7},
                )
                elapsed = time.time() - start_time
                print(
                    f"Anonymization attempt {attempt + 1} successful. Time taken: {elapsed:.2f} seconds."
                )
                print(f"Response: {response.text}")
                self.anonymization_cache[text] = response.text  # Cache the result
                return response.text

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)

        print(f"Anonymization failed for text: {text[:50]}...")
        return None

    def process_database_records(self):
        if not Config.DATABASE_URI:
            print("DATABASE_URI environment variable not set.")
            return

        try:
            print("Connecting to database...")
            conn = psycopg2.connect(Config.DATABASE_URI)
            cur = conn.cursor()

            cur.execute(
                """
                SELECT conversation_pair_id, conversation_a, conversation_b
                FROM conversations
                WHERE contains_pii = true AND opening_msg_pii_removed IS NULL;
                """
            )

            rows = cur.fetchall()
            print(f"Found {len(rows)} rows to process.")

            for row in rows:
                conversation_pair_id, conv_a_json, conv_b_json = row
                print(f"Processing ID: {conversation_pair_id}")

                try:
                    conv_a = conv_a_json
                    conv_b = conv_b_json

                    sanitized_conv_a, opening_msg = self.sanitize_conversation(
                        conv_a, True, conversation_pair_id
                    )
                    sanitized_conv_b, _ = self.sanitize_conversation(
                        conv_b, False, conversation_pair_id
                    )

                    if (
                        sanitized_conv_a
                        and len(sanitized_conv_a) > 0
                        and sanitized_conv_b
                        and len(sanitized_conv_b) > 0
                        and opening_msg
                        and len(opening_msg) > 0
                    ):
                        self.update_database(
                            conversation_pair_id,
                            json.dumps(sanitized_conv_a),
                            json.dumps(sanitized_conv_b),
                            opening_msg,
                        )
                    else:
                        print(
                            f"Not updating db for {conversation_pair_id}, one of those is empty: sanitized_conv_a, sanitized_conv_b, opening_msg"
                        )
                        self.error.append(conversation_pair_id)

                except json.JSONDecodeError as e:
                    print(f"JSON decode error for ID {conversation_pair_id}: {e}")

        except psycopg2.Error as e:
            print(f"Database error: {e}")
        finally:
            print("Errors: ")
            print(str(self.error))
            with open("anon-error.log", "a") as f:
                f.write(f"{self.error}\n")

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
                sanitized_content = self._get_anonymization(
                    text, question_id=conversation_pair_id
                )

                if sanitized_content is not None:
                    sanitized_conversation.append(
                        {"role": "user", "content": sanitized_content}
                    )
                    if get_opening_msg and first_user_message:
                        opening_msg = sanitized_content
                        first_user_message = False
                else:
                    return None, None
            else:
                sanitized_conversation.append(message)

        return sanitized_conversation, opening_msg

    def update_database(
        self, conversation_pair_id, sanitized_conv_a, sanitized_conv_b, opening_msg
    ):
        if not Config.DATABASE_URI:
            print("DATABASE_URI environment variable not set.")
            return

        try:
            print(f"Updating database for conversation_pair_id: {conversation_pair_id}")
            conn = psycopg2.connect(Config.DATABASE_URI)
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
    if Config.DATABASE_URI:
        classifier.process_database_records()


if __name__ == "__main__":
    main()
