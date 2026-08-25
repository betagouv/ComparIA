from utils.database.models.llms.llm import LLMDataUpsert
from utils.utils import FormJsonSchema


def test_system_prompt_is_optional_in_the_admin_form_schema():
    schema = LLMDataUpsert.model_json_schema(schema_generator=FormJsonSchema)

    assert "system_prompt" not in schema["required"]
    assert schema["properties"]["system_prompt"]["optional"] is True
