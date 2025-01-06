import json
from ollama import chat
from pydantic import BaseModel

class Country(BaseModel):
    name: str
    capital: str
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

# Call the LLM using the Ollama chat API
response = chat(
    messages=[
        {
            'role': 'user',
            'content': query_content,
        }
    ],
    model='llama3.1',
    format=Country.model_json_schema(),
)

# Parse the structured response
try:
    country = Country.model_validate_json(response.message.content)
    print(country)
except Exception as e:
    print("Failed to parse the response:", e)
