import json
from openai import OpenAI
from pydantic import BaseModel
from enum import Enum
import os
from collections import defaultdict


# Define the categories as Enum
class TXT360Category(str, Enum):
    arts = "Arts"
    business_economics_finance = "Business & Economics & Finance"
    culture_cultural_geography = "Culture & Cultural geography"
    daily_life_home_lifestyle = "Daily Life & Home & Lifestyle"
    education = "Education"
    entertainment_travel_hobby = "Entertainment & Travel & Hobby"
    environment = "Environment"
    food_drink_cooking = "Food & Drink & Cooking"
    health_wellness_medicine = "Health & Wellness & Medicine"
    law_justice = "Law & Justice"
    natural_science_formal_science_technology = (
        "Natural Science & Formal Science & Technology"
    )
    personal_development_human_resources_career = (
        "Personal Development & Human Resources & Career"
    )
    politics_government = "Politics & Government"
    religion_spirituality = "Religion & Spirituality"
    shopping_commodity = "Shopping & Commodity"
    society_social_issues_human_rights = "Society & Social Issues & Human Rights"
    sports = "Sports"
    other = "Other"


# Define the response model
class SumUp(BaseModel):
    short_summary: str
    keywords: list[str]
    # lmarena_categories: list[str]
    txt360_categories: list[TXT360Category]
    languages: list[str]


client = OpenAI(
    base_url="https://albert.api.etalab.gouv.fr/v1/",
    api_key=os.getenv("ALBERT_API_KEY", ""),
)

# File paths
input_file = "/home/hadrien/git/languia-data/comparia-questions/questions_samples.jsonl"
output_file = "results.jsonl"

# Load already processed conversation_pair_ids
processed_ids = set()
try:
    with open(output_file, "r") as output:
        for line in output:
            try:
                record = json.loads(line)
                processed_ids.add(record["conversation_pair_id"])
            except KeyError:
                pass
except FileNotFoundError:
    # If the output file doesn't exist yet, start fresh
    pass

# Read all records from the input file and organize them by conversation_pair_id
records_by_id = defaultdict(list)
with open(input_file, "r") as file:
    for line in file:
        try:
            record = json.loads(line)
            conversation_pair_id = record.get("conversation_pair_id")
            if conversation_pair_id:
                records_by_id[conversation_pair_id].append(record)
        except json.JSONDecodeError:
            print("Skipping invalid JSON line")

# Prepare the output JSONL
with open(output_file, "a") as output:
    for conversation_pair_id, records in records_by_id.items():
        try:
            # Skip if already processed
            if conversation_pair_id in processed_ids:
                print(
                    f"Skipping already processed conversation_pair_id: {conversation_pair_id}"
                )
                continue

            # Select the record with the highest msg_rank
            record_to_process = max(records, key=lambda r: r.get("msg_rank", 0))

            # question_content = record_to_process.get("question_content")
            # response_a_content = record_to_process.get("response_a_content")
            # response_b_content = record_to_process.get("response_b_content")
            conversation_a = json.dumps(record_to_process.get("conversation_a"))
            conversation_b = json.dumps(record_to_process.get("conversation_b"))

            # Formulate the query
            query_content = f"""
            Based on the following two conversations between a user and 2 different bots, provide some keywords in the requested format.
            """
            # query_content = f"""
            # Based on the following two between a user and 2 bots, provide some keywords in the requested format.
            # """

            # Make the OpenAI API call
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": query_content},
                    {"role": "user", "content": conversation_a},
                    {"role": "user", "content": conversation_b},
                    # {"role": "user", "content": question_content},
                    # {"role": "user", "content": response_a_content},
                    # {"role": "user", "content": response_b_content},
                ],
                temperature=0.3,
                model="meta-llama/Meta-Llama-3.1-70B-Instruct",
                extra_body={"guided_json": SumUp.model_json_schema()},
            )
            print(response.__dict__)

            # Parse the response into the SumUp model
            sum_up = SumUp.model_validate_json(response.choices[0].message.content)

            # Write the result to the output JSONL
            result = {
                "conversation_pair_id": conversation_pair_id,
                "short_summary": sum_up.short_summary,
                "keywords": sum_up.keywords,
                "txt360_categories": sum_up.txt360_categories,
                "languages": sum_up.languages,
            }
            output.write(json.dumps(result) + "\n")
            processed_ids.add(conversation_pair_id)  # Mark as processed
            print(f"Processed conversation_pair_id: {conversation_pair_id}")
        except Exception as e:
            print(
                f"Failed to process record for conversation_pair_id {conversation_pair_id}: {e}"
            )
            continue
