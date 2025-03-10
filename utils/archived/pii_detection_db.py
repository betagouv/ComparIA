import psycopg2
import json
import time
import vertexai
from vertexai.generative_models import GenerativeModel
from typing import Optional
import os


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
                    print(
                        f"Text: '{text[:50]}...', Result: {result}, Time: {elapsed:.2f}s"
                    )
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

def get_conv_b_index(conversation_a, conversation_b, a_index):

    if not conversation_a or not conversation_b:
        return None

    offset_a = (
        1 if conversation_a and conversation_a[0].get("role") == "system" else 0
    )
    offset_b = (
        1 if conversation_b and conversation_b[0].get("role") == "system" else 0
    )

    return a_index - offset_a + offset_b


def process_conversations(db_params, classifier: PrivacyClassifier):
    try:
        conn = psycopg2.connect(db_params)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT conversation_pair_id, conversation_a, conversation_b FROM conversations WHERE pii_analyzed = FALSE;"
        )
        conversations = cursor.fetchall()

        # Check if CSV file exists and write header if not
        csv_exists = os.path.exists("pii_question_ids.csv")
        if not csv_exists:
            with open("pii_question_ids.csv", "w") as f:
                f.write("q_id_a,q_id_b,contains_pii\n")

        for conversation_id, conversation_a, conversation_b in conversations:
            contains_pii = False
            pii_messages = []

            # Analyze conversation_a
            if conversation_a:
                for msg_index, message in enumerate(conversation_a):
                    if message.get("role") == "user":
                        question_content = message.get("content", "")
                        if classifier.analyze_text(question_content):
                            contains_pii = True
                            a_q_id = f"{conversation_id}-{msg_index}"
                            b_q_id = f"{conversation_id}-{get_conv_b_index(conversation_a, conversation_b, msg_index)}"
                            pii_messages.append(f"{a_q_id},{b_q_id},true")
                        else:
                            a_q_id = f"{conversation_id}-{msg_index}"
                            b_q_id = f"{conversation_id}-{get_conv_b_index(conversation_a, conversation_b, msg_index)}"
                            pii_messages.append(f"{a_q_id},{b_q_id},false")

            cursor.execute(
                "UPDATE conversations SET pii_analyzed = TRUE, contains_pii = %s WHERE conversation_pair_id = %s;",
                (contains_pii, conversation_id),
            )
            conn.commit()

            # Append PII messages to CSV
            if pii_messages:
                with open("pii_question_ids.csv", "a") as f:
                    for q_id in pii_messages:
                        f.write(q_id + "\n")

        print("Conversations processed successfully.")

    except psycopg2.Error as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()


db_params = os.getenv("DATABASE_URI")

classifier = PrivacyClassifier()
process_conversations(db_params, classifier)
