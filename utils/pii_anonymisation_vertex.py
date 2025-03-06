import json
import argparse
from pathlib import Path
import logging
from typing import List, Set, Optional
from tqdm import tqdm
import vertexai
from vertexai.generative_models import GenerativeModel
import time
import pandas as pd

import difflib


class Config:
    PROJECT_ID = "languia-430909"  # Update with your GCP project ID
    LOCATION = "europe-west1"  # Update with your preferred location
    MODEL_NAME = "gemini-2.0-flash"
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    BATCH_SIZE = 50
    SAVE_INTERVAL = 50
    DEFAULT_SAMPLE_SIZE = None

    PROMPT_TEMPLATE = (
        "Task: Replace the parts of the text that contains personal, sensitive, or private information with '********'.\n"
        "Original text: {text}\n"
        "Replaced text: "
    )


class Classifier:
    def __init__(self, output_dir: str = "results-anonymization"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()
        self.model = self._initialize_model()
        self.processed_ids = set()
        self._load_processed_ids()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(self.output_dir / "classification.log"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def _initialize_model(self):
        try:
            vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
            return GenerativeModel(Config.MODEL_NAME)
        except Exception as e:
            self.logger.error(f"Model initialization failed: {str(e)}")
            return None

    def _load_processed_ids(self):
        try:
            with open(self.output_dir / "anonymized.jsonl", "r") as f:
                for line in f:
                    record = json.loads(line)
                    self.processed_ids.add(record["question_id"])
                print(
                    "Loaded " + str(len(self.processed_ids)) + " already processed IDs."
                )
        except FileNotFoundError:
            pass

    def _get_anonymization(self, question_id, text: str) -> Optional[bool]:
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

                content = response.text
                # self.stats.add_result(content, elapsed)
                return {"question_id": question_id, "text": text, "redacted": content}
                # if content in ['true', 'false']:
                #     result = content == 'true'
                #     return result
                # else:
                #     self.logger.warning(f"Unexpected response: {response.text}")

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
        return None

    def calculate_diff(self, input_str, result_str):
        """
        Calculate the difference between two strings using difflib.

        Args:
            input_str (str): The original string.
            result_str (str): The modified string.

        Returns:
            A generator yielding the differences between the two strings.
        """
        diff = difflib.Differ()
        return diff.compare(input_str.splitlines(), result_str.splitlines())

    def process_batch(self, batch) -> List[dict]:
        results = []

        for index, record in tqdm(batch.iterrows(), desc="Processing entries"):
            question_id = record.question_id
            if question_id in self.processed_ids:
                print("Skipping already processed ID: " + question_id)
                continue
            print("Processing ID: " + question_id)
            result = self._get_anonymization(question_id, record.text)

            if result:

                diff = self.calculate_diff(record.text, result["redacted"])

                for line in diff:
                    if line.startswith("+ "):
                        print(f"\033[92m{line}\033[0m")  # Green for added lines
                    elif line.startswith("- "):
                        print(f"\033[91m{line}\033[0m")  # Red for removed lines
                    elif line.startswith("? "):
                        print(f"\033[93m{line}\033[0m")  # Yellow for context lines
                    else:
                        print(line)
                # input()
                results.append(result)
                self._save_results([result])
                self.processed_ids.add(question_id)

        return results

    def _save_results(self, results: List[dict]):
        try:
            with open(self.output_dir / "anonymized.jsonl", "a") as f:
                for res in results:
                    f.write(json.dumps(res) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to save results: {str(e)}")

    def process_dataset(self, file_path: str, num_samples: Optional[int] = None):
        # try:
        # ds = load_dataset("ministere-culture/comparia-questions", token=hf_token)
        df = pd.read_csv(file_path)

        pii_df = df[df["contains_sensitive_info"] == "True"]

        total_available = len(pii_df)
        print("Total lines to analyze: " + str(total_available))
        num_samples = num_samples or total_available

        self.logger.info(f"Processing {num_samples} out of {total_available} questions")

        all_results = []
        for i in range(0, num_samples):
            batch_results = self.process_batch(pii_df)
            all_results.extend(batch_results)

    # except Exception as e:
    #     self.logger.error(f"Processing dataset failed: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Conversation Analyzer")
    parser.add_argument("--file", type=str, required=True, help="Path of input CSV")
    parser.add_argument(
        "--samples",
        type=int,
        default=Config.DEFAULT_SAMPLE_SIZE,
        help="Number of samples to process",
    )
    parser.add_argument(
        "--output", type=str, default="results-output", help="Output directory"
    )

    args = parser.parse_args()

    analyzer = Classifier(output_dir=args.output)
    analyzer.process_dataset(file_path=args.file, num_samples=args.samples)


if __name__ == "__main__":
    main()
