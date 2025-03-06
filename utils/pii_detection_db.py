import psycopg2
import json
import time
import vertexai
from vertexai.generative_models import GenerativeModel
from typing import Optional

class Config:
    PROJECT_ID = "languia-430909"
    LOCATION = "europe-west1"
    MODEL_NAME = "gemini-2.0-flash-001"
    MAX_RETRIES = 3
    RETRY_DELAY = 1

    PROMPT_TEMPLATE = (
        "Task: Identify if text contains personal, sensitive, or private information.\n"
        "Rules:\n"
        "- Answer ONLY with single word 'true' or 'false'\n"
        "- true = contains personal info (names, emails, addresses) or sensitive info (medical, financial)\n"
        "- false = no personal or sensitive info\n\n"
        "Text: {text}\n"
        "Answer: "
    )

class PrivacyClassifier:
    def __init__(self):
        self.model = self._initialize_model()

    def _initialize_model(self):
        try:
            vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
            return GenerativeModel(Config.MODEL_NAME)
        except Exception as e:
            print(f"Model initialization failed: {str(e)}")
            return None

    def _get_classification(self, text: str) -> Optional[bool]:
        prompt = Config.PROMPT_TEMPLATE.format(text=text)

        for attempt in range(Config.MAX_RETRIES):
            try:
                start_time = time.time()
                response = self.model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.7, "max_output_tokens": 1},
                )
                elapsed = time.time() - start_time
                content = response.text.lower().strip().rstrip(".")

                if content in ["true", "false"]:
                    result = content == "true"
                    print(f"Text: '{text[:50]}...', Result: {result}, Time: {elapsed:.2f}s")
                    return result
                else:
                    print(f"Warning: Unexpected response: {response.text}")

            except Exception as e:
                print(f"Warning: Attempt {attempt + 1} failed: {str(e)}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)

        print(f"Error: max retries reached for text: '{text[:50]}...'")
        return None

    def analyze_text(self, text: str) -> Optional[bool]:
        return self._get_classification(text)

def process_conversations(db_params, classifier: PrivacyClassifier):
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        cursor.execute("SELECT id, conversation_a FROM conversations WHERE pii_analyzed = FALSE;")
        conversations = cursor.fetchall()

        pii_question_ids = []  # List to store question IDs with PII

        for conversation_id, conversation_a in conversations:
            contains_pii = False
            if conversation_a:
                for msg_index, message in enumerate(conversation_a):
                    if message.get("role") == "user":
                        question_content = message.get("content", "")
                        if classifier.analyze_text(question_content):
                            contains_pii = True
                            pii_question_ids.append(f"{conversation_id}-{msg_index},true") #added to list.

            cursor.execute(
                "UPDATE conversations SET pii_analyzed = TRUE, contains_pii = %s WHERE id = %s;",
                (contains_pii, conversation_id),
            )

        conn.commit()
        print("Conversations processed successfully.")

        # Save PII question IDs to a CSV file
        if pii_question_ids:
            with open("pii_question_ids.txt", "w") as f:
                f.write("q_id\n")  # Write header
                for q_id in pii_question_ids:
                    f.write(q_id + "\n")
            print("\nPII question IDs saved to pii_question_ids.txt")
        else:
            print("\nNo PII found in the processed conversations.")

    except psycopg2.Error as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()

# # Example usage
# db_params = {
#     "dbname": "your_dbname",
#     "user": "your_user",
#     "password": "your_password",
#     "host": "your_host",
#     "port": "your_port",
# }

# classifier = PrivacyClassifier()
# process_conversations(db_params, classifier)