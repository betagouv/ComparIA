import json
import argparse
from pathlib import Path
import logging
from typing import List, Set, Optional
from collections import defaultdict
from tqdm import tqdm

# Removed vertexai import
import time
import pandas as pd
import difflib
import google.cloud.dlp
from datetime import datetime


class Config:
    PROJECT_ID = "languia-430909"  # Update with your GCP project ID
    LOCATION = "europe-west1"  # This is not used by DLP, but kept for consistency
    # MODEL_NAME = "gemini-2.0-flash"  # No longer needed
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    BATCH_SIZE = 50
    SAVE_INTERVAL = 50
    DEFAULT_SAMPLE_SIZE = None
    DLP_INFO_TYPES = [
        "FRANCE_CNI",
        "PASSPORT",
        "STREET_ADDRESS",
        "EMAIL_ADDRESS",
        "CREDIT_CARD_NUMBER",
        "PERSON_NAME",
        "DATE_OF_BIRTH",
        "IP_ADDRESS",
        "PHONE_NUMBER",
        "SWIFT_CODE",
        "GOVERNMENT_ID",
    ]
    MASKING_CHARACTER = "*"
    NUMBER_TO_MASK = 0  # 0 masks all occurrences
    OUTPUT_SUFFIX = "_anonymized"


class Classifier:
    def __init__(
        self,
        output_dir: str = "results-anonymization",
        output_suffix: str = Config.OUTPUT_SUFFIX,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_suffix = output_suffix
        self._setup_logging()
        # self.model = self._initialize_model()  # No longer needed
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

    # No need for model initialization as we're using DLP now
    # def _initialize_model(self):
    #     try:
    #         vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
    #         return GenerativeModel(Config.MODEL_NAME)
    #     except Exception as e:
    #         self.logger.error(f"Model initialization failed: {str(e)}")
    #         return None

    def _load_processed_ids(self):
        try:
            with open(self.output_dir / "anonymized-dlp.jsonl", "r") as f:
                for line in f:
                    record = json.loads(line)
                    self.processed_ids.add(record["question_id"])
                print(
                    "Loaded " + str(len(self.processed_ids)) + " already processed IDs."
                )
        except FileNotFoundError:
            pass

    def _get_anonymization(self, question_id, text: str) -> Optional[dict]:
        """Get anonymization from DLP"""

        for attempt in range(Config.MAX_RETRIES):
            try:
                start_time = time.time()
                redacted_text = deidentify_with_mask(
                    project=Config.PROJECT_ID,
                    input_str=text,
                    info_types=Config.DLP_INFO_TYPES,
                    masking_character=Config.MASKING_CHARACTER,
                    number_to_mask=Config.NUMBER_TO_MASK,
                )
                elapsed = time.time() - start_time
                return {
                    "question_id": question_id,
                    "text": text,
                    "redacted": redacted_text,
                }

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed", exc_info=True)
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
            with open(self.output_dir / "anonymized-dlp.jsonl", "a") as f:
                for res in results:
                    f.write(json.dumps(res) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to save results: {str(e)}")

    def process_dataset(self, file_path: str, num_samples: Optional[int] = None):
        try:
            df = pd.read_csv(file_path)

            pii_df = df[df["contains_sensitive_info"] == "True"]

            total_available = len(pii_df)
            print("Total lines to analyze: " + str(total_available))
            num_samples = num_samples or total_available

            self.logger.info(
                f"Processing {num_samples} out of {total_available} questions"
            )

            all_results = []
            for i in range(0, num_samples):
                batch_results = self.process_batch(pii_df)
                all_results.extend(batch_results)

            # Save the anonymized data to a new CSV file
            self._export_anonymized_data(df, all_results, file_path)

        except Exception as e:
            self.logger.error(f"Processing dataset failed: {str(e)}")

    def _export_anonymized_data(
        self,
        original_df: pd.DataFrame,
        anonymized_results: List[dict],
        original_file_path: str,
    ):
        """
        Exports the anonymized data to a new CSV and TSV file, based on the original file.
        """
        if not anonymized_results:
            self.logger.info("No anonymized results to export.")
            return

        # Create a dictionary to map question_ids to anonymized texts.  This handles cases where the original
        # dataframe has some issues (e.g. missing IDs or duplicate IDs)
        anonymized_texts = {
            result["question_id"]: result["redacted"] for result in anonymized_results
        }

        # Create a copy of the original DataFrame to avoid modifying it directly
        anonymized_df = original_df.copy()

        # Apply the anonymization; use .loc for efficient and precise assignment.  If the ID isn't found, the redacted text is set to an empty string
        anonymized_df["anonymized_text"] = anonymized_df["question_id"].apply(
            lambda id: anonymized_texts.get(id, "")
        )

        # Construct the new file names
        file_path = Path(original_file_path)
        base_name = file_path.stem
        csv_output_file = self.output_dir / f"{base_name}{self.output_suffix}.csv"
        tsv_output_file = self.output_dir / f"{base_name}{self.output_suffix}.tsv"

        # Save to CSV
        try:
            anonymized_df.to_csv(csv_output_file, index=False)
            self.logger.info(f"Anonymized data saved to: {csv_output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save anonymized data to CSV: {str(e)}")

        # Save to TSV
        try:
            anonymized_df.to_csv(tsv_output_file, sep="\t", index=False)
            self.logger.info(f"Anonymized data saved to: {tsv_output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save anonymized data to TSV: {str(e)}")


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
    parser.add_argument(
        "--suffix",
        type=str,
        default=Config.OUTPUT_SUFFIX,
        help="Suffix for output files (e.g., _anonymized)",
    )

    args = parser.parse_args()

    analyzer = Classifier(output_dir=args.output, output_suffix=args.suffix)
    analyzer.process_dataset(file_path=args.file, num_samples=args.samples)


def deidentify_with_mask(
    project: str,
    input_str: str,
    info_types: List[str],
    masking_character: str = None,
    number_to_mask: int = 0,
) -> str:
    """Uses the Data Loss Prevention API to deidentify sensitive data in a
    string by masking it with a character.
    Args:
        project: The Google Cloud project id to use as a parent resource.
        input_str: The string to deidentify (will be treated as text).
        info_types: A list of strings representing info types to look for.
            A full list of info type categories can be fetched from the API.
        masking_character: The character to mask matching sensitive data with.
        number_to_mask: The maximum number of sensitive characters to mask in
            a match. If omitted or set to zero, the API will default to no
            maximum.
    Returns:
         The deidentified string
    """

    # Instantiate a client
    dlp = google.cloud.dlp_v2.DlpServiceClient()

    # Convert the project id into a full resource id.
    parent = f"projects/{project}/locations/global"

    # Construct inspect configuration dictionary
    inspect_config = {"info_types": [{"name": info_type} for info_type in info_types]}

    # Construct deidentify configuration dictionary
    deidentify_config = {
        "info_type_transformations": {
            "transformations": [
                {
                    "primitive_transformation": {
                        "character_mask_config": {
                            "masking_character": masking_character,
                            "number_to_mask": number_to_mask,
                        }
                    }
                }
            ]
        }
    }

    # Construct item
    item = {"value": input_str}

    # Call the API
    response = dlp.deidentify_content(
        request={
            "parent": parent,
            "deidentify_config": deidentify_config,
            "inspect_config": inspect_config,
            "item": item,
        }
    )

    # Return the deidentified string.
    return response.item.value


if __name__ == "__main__":
    main()
