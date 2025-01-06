import json
from openai import OpenAI

# from litellm import completion
from pydantic import BaseModel
from enum import Enum
import os


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


# Read the JSONL input file
input_file = "/home/hadrien/git/languia-data/comparia-questions/questions_samples.jsonl"  # Replace with your actual JSON file path
output_file = "results.jsonl"

# Open the input JSONL file
with open(input_file, "r") as file:
    lines = file.readlines()

# Prepare the output JSONL
with open(output_file, "w") as output:
    for line in lines:
        try:
            # Parse each line as a JSON object
            record = json.loads(line)
            question_content = record.get("conv_a")
            response_a_content = record.get("response_a_content")
            response_b_content = record.get("response_b_content")
            conversation_pair_id = record.get("conversation_pair_id")

            if not conversation_pair_id:
                print(f"Skipping record without 'conversation_pair_id'")
                continue

            # Formulate the query
            query_content = f"""
            Based on the following exchange between a user and 2 bots, provide some keywords in the requested format.
            """

            # ================================
            # BEGINNING OF CONV A:

            # {conv_a}

            # ================================
            # END OF CONV A

            # ================================
            # BEGINNING OF CONV B:

            # {conv_b}

            # ================================
            # END OF CONV B

            # Make the litellm API call
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": query_content,
                    },
                    {
                        "role": "user",
                        "content": question_content,
                    },
                    {
                        "role": "user",
                        "content": response_a_content,
                    },
                    {
                        "role": "user",
                        "content": response_b_content,
                    },
                ],
                temperature=0.7,
                model="openai/meta-llama/Meta-Llama-3.1-70B-Instruct",
                extra_body={"guided_json": SumUp.model_json_schema()},
                # format=SumUp.model_json_schema()
            )

            # Parse the response into the SumUp model
            sum_up = SumUp.model_validate_json(response.message.content)

            # Write the result to the output JSONL
            result = {
                "conversation_pair_id": conversation_pair_id,
                "short_summary": sum_up.short_summary,
                "keywords": sum_up.keywords,
                "txt360_categories": sum_up.txt360_categories,
                "languages": sum_up.languages,
            }
            output.write(json.dumps(result) + "\n")
            print(f"Processed conversation_pair_id: {conversation_pair_id}")
            input("Press any key for next conv...")
        except Exception as e:
            print(f"Failed to process record: {e}")
            input("Press any key for next conv...")
