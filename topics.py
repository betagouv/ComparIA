import json
from litellm import completion
from pydantic import BaseModel
from enum import Enum

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

class SumUp(BaseModel):
    short_summary: str
    keywords: list[str]
    # lmarena_categories: list[str]

    txt360_categories: list[TXT360Category]

    languages: list[str]

# Read the .json file and extract the 'conv_a' JSON object
input_file = 'your_file.json'  # Replace with your actual JSON file path
with open(input_file, 'r') as file:
    data = json.load(file)

conv_a = data.get('conv_a')

if not conv_a:
    raise ValueError("The JSON object 'conv_a' is not found in the file.")

# Use the content from 'conv_a' to formulate a query
query_content = f"Based on the conversation: {conv_a}, provide some keywords."

#   //   "model_id": "llama-3.1-70b",
#   //   "api_id": "albert-llama-3.1-70b",
#   //   "api_base": "https://albert.api.etalab.gouv.fr/v1/",
#   //   "api_type": "openai",
#   //   "api_key": "langia-",
#   //   "model_name": "meta-llama/Meta-Llama-3.1-70B-Instruct",
#   //   "recommended_config": {
#   //     "temperature": 0.7,
response = completion(
    messages=[
        {
            'role': 'user',
            'content': query_content,
        }
    ],
    
    model='llama3.1',
    format=SumUp.model_json_schema(),
)

# Parse the structured response
try:
    sum_up = SumUp.model_validate_json(response.message.content)
    print(sum_up)
except Exception as e:
    print("Failed to parse the response:", e)
