from utils.database.models.llms import (
    LLMDataUpsert,
    LLMEndpointUpsert,
    LLMLabUpsert,
    LLMLicenseUpsert,
)
from utils.utils import (
    FRONTEND_MAIN_I18N_FILE,
    FormJsonSchema,
    read_json,
    sort_dict,
    write_json,
)


def get_property_i18n(prop):
    data = {"label": prop["title"]}
    if help_ := prop.get("description"):
        data["help"] = help_

    return data


def get_schema_i18n(schema, refs):
    data = {}

    if schema["type"] == "object":
        for k, v in schema["properties"].items():
            if ref := v.get("$ref"):
                ref = ref.split("/")[-1]
                data[ref] = get_schema_i18n(refs[ref], refs)
            else:
                data[k] = get_property_i18n(v)
    else:
        data[k] = get_property_i18n(schema)

    return data


def generate_admin_schemas_i18n():
    models = {
        "endpoint_upsert": LLMEndpointUpsert,
        "license_upsert": LLMLicenseUpsert,
        "lab_upsert": LLMLabUpsert,
        "llm_upsert": LLMDataUpsert,
    }
    schemas = {
        k: model.model_json_schema(schema_generator=FormJsonSchema)
        for k, model in models.items()
    }
    data = {
        k: get_schema_i18n(schema, schema.get("$defs", {}))
        for k, schema in schemas.items()
    }

    frontend_i18n = read_json(FRONTEND_MAIN_I18N_FILE)
    frontend_i18n["generated"] = sort_dict({**frontend_i18n["generated"], **data})
    write_json(FRONTEND_MAIN_I18N_FILE, frontend_i18n, indent=4)
