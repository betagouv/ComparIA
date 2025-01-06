import json
from litellm import completion
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
    natural_science_formal_science_technology = "Natural Science & Formal Science & Technology"
    personal_development_human_resources_career = "Personal Development & Human Resources & Career"
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

# Read the JSONL input file
input_file = '/home/hadrien/git/languia-data/comparia-questions/questions_samples.jsonl'  # Replace with your actual JSON file path
output_file = 'results.jsonl'

# Open the input JSONL file
with open(input_file, 'r') as file:
    lines = file.readlines()

# Prepare the output JSONL
with open(output_file, 'w') as output:
    for line in lines:
        try:
            # Parse each line as a JSON object
            record = json.loads(line)
            conv_a = record.get('conv_a')
            conversation_pair_id = record.get('conversation_pair_id')

            if not conv_a or not conversation_pair_id:
                print(f"Skipping record without 'conv_a' or 'conversation_pair_id': {record}")
                continue

            # Formulate the query
            query_content = f"Based on the conversation: {conv_a}, provide some keywords."

            # Make the litellm API call
            response = completion(temperature=0.7,
                messages=[
                    {
                        'role': 'user',
                        'content': query_content,
                    }
                ],
                api_key=os.getenv("ALBERT_API_KEY", ""),
                api_base="https://albert.api.etalab.gouv.fr/v1/"
                model='meta-llama/Meta-Llama-3.1-70B-Instruct',
                format=SumUp.model_json_schema(),
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
            output.write(json.dumps(result) + '\n')
            print(f"Processed conversation_pair_id: {conversation_pair_id}")

        except Exception as e:
            print(f"Failed to process record: {e}")
