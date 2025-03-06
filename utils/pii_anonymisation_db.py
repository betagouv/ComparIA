import json
import vertexai
from vertexai.generative_models import GenerativeModel
import time
import os
import psycopg2

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

class Classifier:
    def __init__(self):
        self.model = self._initialize_model()

    def _initialize_model(self):
        try:
            vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
            return GenerativeModel(Config.MODEL_NAME)
        except Exception as e:
            print(f"Model initialization failed: {str(e)}")
            return None

    def _get_anonymization(self, text: str) -> Optional[str]:
        """Get anonymization from model with retries"""
        prompt = Config.PROMPT_TEMPLATE.format(text=text)

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

                return response.text

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
        return None

    def process_database_records(self):
        if not Config.CONNECTION_URI:
            print("CONNECTION_URI environment variable not set.")
            return

        try:
            conn = psycopg2.connect(Config.CONNECTION_URI)
            cur = conn.cursor()

            cur.execute(
                """
                SELECT conversation_pair_id, conversation_a, conversation_b
                FROM conversations
                WHERE pii_detected = true AND opening_msg_pii_removed = NULL;
                """
            )

            rows = cur.fetchall()

            for row in rows:
                conversation_pair_id, conv_a_json, conv_b_json = row
                print(f"Processing ID: {conversation_pair_id}")

                try:
                    conv_a = json.loads(conv_a_json)
                    conv_b = json.loads(conv_b_json)

                    sanitized_conv_a = self.sanitize_conversation(conv_a)
                    sanitized_conv_b = self.sanitize_conversation(conv_b)

                    self.update_database(conversation_pair_id, json.dumps(sanitized_conv_a), json.dumps(sanitized_conv_b))

                except json.JSONDecodeError as e:
                    print(f"JSON decode error for ID {question_id}: {e}")

        except psycopg2.Error as e:
            print(f"Database error: {e}")
        finally:
            if conn:
                cur.close()
                conn.close()

    def sanitize_conversation(self, conversation):
        sanitized_conversation = []
        for message in conversation:
            if message.get("role") == "user":
                sanitized_content = self._get_anonymization(message.get("content", ""))
                if sanitized_content is not None:
                    sanitized_conversation.append({"role": "user", "content": sanitized_content})
                else:
                    sanitized_conversation.append(message) # if fail keep original
            else:
                sanitized_conversation.append(message)
        return sanitized_conversation

    def update_database(self, conversation_pair_id, sanitized_conv_a, sanitized_conv_b):
        """Update the database with the redacted conversations."""
        if not Config.CONNECTION_URI:
            print("CONNECTION_URI environment variable not set.")
            return

        try:
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
            print(f"Updated database for conversation_pair_id: {conversation_pair_id}")

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