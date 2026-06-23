"""add LLMData, LLMEndpoint, LLMLab, LLMLicence

Revision ID: 4e31217520dd
Revises: 89de92001a7e
Create Date: 2026-06-15 11:00:43.707153

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4e31217520dd"
down_revision: Union[str, Sequence[str], None] = "89de92001a7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# start custom
import json
import os
from datetime import datetime

from utils.utils import LLMS_LICENSES_FILE, LLMS_RAW_DATA_FILE


def parse_date(d: str) -> datetime:
    month, year = d.split("/")
    return datetime(int(year), int(month), 1)


def add_base_info(raw_data, date):
    raw_data["id"] = raw_data["db_id"]
    raw_data["created_at"] = date
    raw_data["updated_at"] = date
    return raw_data


def get_new_llms_raw_data():
    OPENROUTER_ENDPOINT_ID = "9667ee84-9b07-4d3d-890c-57fc9ffe9c33"
    HUGGINGFACE_ENDPOINT_ID = "3f9547a8-6033-4223-98f4-2245d3be4a3d"
    ORDBOGEN_ENDPOINT_ID = "24a47a21-d767-4352-8de8-be188b2863f9"

    raw_endpoints = [
        {
            "id": OPENROUTER_ENDPOINT_ID,
            "name": "OpenRouter",
            "api_type": "openrouter",
            "api_base": None,
            "api_version": None,
            "api_key": os.getenv("OPENROUTER_API_KEY"),
        },
        {
            "id": HUGGINGFACE_ENDPOINT_ID,
            "name": "Hugging Face",
            "api_type": "huggingface",
            "api_base": "https://router.huggingface.co/v1",
            "api_version": None,
            "api_key": os.getenv("HF_INFERENCE_KEY"),
        },
        {
            "id": ORDBOGEN_ENDPOINT_ID,
            "name": "Ordbogen",
            "api_type": "openai",
            "api_base": "https://api.ordbogen.ai/v1",
            "api_version": None,
            "api_key": os.getenv("ORDBOGEN_API_KEY"),
        },
    ]
    raw_orgas = json.loads(LLMS_RAW_DATA_FILE.read_text())
    raw_licenses = json.loads(LLMS_LICENSES_FILE.read_text())

    endpoints = []
    licenses = []
    labs = []
    llms = []

    base_date = datetime.now()
    for raw_endpoint in raw_endpoints:
        raw_endpoint["created_at"] = base_date
        raw_endpoint["updated_at"] = base_date
        endpoints.append(raw_endpoint)

    for raw_license in raw_licenses:
        add_base_info(raw_license, base_date)

        raw_license["name"] = raw_license["license"]
        raw_license["kind"] = (
            "proprietary"
            if raw_license["distribution"] == "api-only"
            else "open-weights"
        )
        raw_license["commercial_use"] = raw_license.get("commercial_use", False)

        licenses.append(raw_license)

    for raw_orga in raw_orgas:
        raw_llms = raw_orga.pop("models")

        add_base_info(raw_orga, base_date)

        raw_orga["logo"] = raw_orga["icon_path"]

        labs.append(raw_orga)

        for raw_llm in raw_llms:
            if raw_llm.get("status") == "missing_data":
                continue

            raw_llm["human_id"] = raw_llm["id"]
            add_base_info(raw_llm, base_date)

            raw_llm["lab_id"] = raw_orga["id"]
            license = next(l for l in licenses if l["name"] == raw_llm["license"])
            raw_llm["license_id"] = license["id"]

            raw_llm["status"] = raw_llm.get("status", "enabled")
            raw_llm["name"] = raw_llm["simple_name"]
            raw_llm["release_date"] = parse_date(raw_llm["release_date"])
            raw_llm["system_prompt"] = raw_llm.get("system_prompt", None)
            raw_llm["active_params"] = raw_llm.get("active_params", None)
            raw_llm["quantization"] = raw_llm.get("quantization", None)
            raw_llm["rate_limited"] = raw_llm.get("pricey", False)

            raw_llm["endpoint_id"] = None
            if endpoint := raw_llm.get("endpoint"):
                raw_llm["api_model_id"] = endpoint["api_model_id"]
                if raw_llm["status"] == "enabled":
                    if "ordbogen" in endpoint.get("api_base", ""):
                        raw_llm["endpoint_id"] = ORDBOGEN_ENDPOINT_ID
                    elif "huggingface" in endpoint.get("api_base", ""):
                        raw_llm["endpoint_id"] = HUGGINGFACE_ENDPOINT_ID
                    else:
                        raw_llm["endpoint_id"] = OPENROUTER_ENDPOINT_ID
            else:
                raw_llm["status"] = "disabled"
                raw_llm["api_model_id"] = None

            if url := raw_llm.get("url"):
                link = {
                    "text": "Hugging Face" if "hugging" in url else "link",
                    "url": url,
                }
                raw_llm["links"] = [link]
            else:
                raw_llm["links"] = []

            llms.append(raw_llm)

    return {
        "llm_endpoint": endpoints,
        "llm_license": licenses,
        "llm_lab": labs,
        "llm_data": llms,
    }


def inject_llms_data() -> None:
    data = get_new_llms_raw_data()

    tables_data = {
        "llm_endpoint": {
            "id": sa.Uuid,
            "created_at": postgresql.TIMESTAMP,
            "updated_at": postgresql.TIMESTAMP,
            "name": sqlmodel.sql.sqltypes.AutoString,
            "api_type": sqlmodel.sql.sqltypes.AutoString,
            "api_base": sqlmodel.sql.sqltypes.AutoString,
            "api_version": sqlmodel.sql.sqltypes.AutoString,
            "api_key": sqlmodel.sql.sqltypes.AutoString,
        },
        "llm_lab": {
            "id": sa.Uuid,
            "created_at": postgresql.TIMESTAMP,
            "updated_at": postgresql.TIMESTAMP,
            "name": sqlmodel.sql.sqltypes.AutoString,
            "logo": sqlmodel.sql.sqltypes.AutoString,
            "origin_country": sqlmodel.sql.sqltypes.AutoString,
        },
        "llm_license": {
            "id": sa.Uuid,
            "created_at": postgresql.TIMESTAMP,
            "updated_at": postgresql.TIMESTAMP,
            "kind": sa.String,
            "name": sqlmodel.sql.sqltypes.AutoString,
            "reuse": sa.Boolean,
            "commercial_use": sa.Boolean,
        },
        "llm_data": {
            "id": sa.Uuid,
            "created_at": postgresql.TIMESTAMP,
            "updated_at": postgresql.TIMESTAMP,
            "lab_id": sa.Uuid,
            "license_id": sa.Uuid,
            "endpoint_id": sa.Uuid,
            "human_id": sqlmodel.sql.sqltypes.AutoString,
            "api_model_id": sqlmodel.sql.sqltypes.AutoString,
            "status": sa.String,
            "name": sqlmodel.sql.sqltypes.AutoString,
            "rate_limited": sa.Boolean,
            "release_date": postgresql.TIMESTAMP,
            "knowledge_cutoff": postgresql.TIMESTAMP,
            "arch": sa.String,
            "params": sa.Float,
            "active_params": sa.Float,
            "context_tokens": sa.Integer,
            "quantization": sa.String,
            "inputs": postgresql.JSONB,
            "public_weights": sa.Boolean,
            "public_training_data": sa.Boolean,
            "public_training_code": sa.Boolean,
            "eu_hostable": sa.Boolean,
            "price_in": sa.Float,
            "price_out": sa.Float,
            "system_prompt": sqlmodel.sql.sqltypes.AutoString,
            "links": postgresql.JSONB,
        },
    }

    for table_name, columns in tables_data.items():
        table = sa.table(table_name, *[sa.column(k, v) for k, v in columns.items()])
        op.execute(
            table.insert().values(
                [{k: item[k] for k in columns.keys()} for item in data[table_name]]
            )
        )


# end custom


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "llm_endpoint",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("api_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("api_base", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("api_version", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("api_key", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_llm_endpoint_name"), "llm_endpoint", ["name"], unique=False
    )
    op.create_table(
        "llm_lab",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("logo", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("origin_country", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "llm_license",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("reuse", sa.Boolean(), nullable=False),
        sa.Column("commercial_use", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "llm_data",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("lab_id", sa.Uuid(), nullable=False),
        sa.Column("license_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint_id", sa.Uuid(), nullable=True),
        sa.Column("human_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("api_model_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("rate_limited", sa.Boolean(), nullable=False),
        sa.Column("release_date", postgresql.TIMESTAMP(), nullable=False),
        sa.Column("knowledge_cutoff", postgresql.TIMESTAMP(), nullable=True),
        sa.Column("arch", sa.String(), nullable=False),
        sa.Column("params", sa.Float(), nullable=False),
        sa.Column("active_params", sa.Float(), nullable=True),
        sa.Column("context_tokens", sa.Integer(), nullable=True),
        sa.Column("quantization", sa.String(), nullable=True),
        sa.Column("inputs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("public_weights", sa.Boolean(), nullable=False),
        sa.Column("public_training_data", sa.Boolean(), nullable=False),
        sa.Column("public_training_code", sa.Boolean(), nullable=False),
        sa.Column("eu_hostable", sa.Boolean(), nullable=False),
        sa.Column("price_in", sa.Float(), nullable=False),
        sa.Column("price_out", sa.Float(), nullable=False),
        sa.Column("system_prompt", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("links", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["endpoint_id"], ["llm_endpoint.id"]),
        sa.ForeignKeyConstraint(["lab_id"], ["llm_lab.id"]),
        sa.ForeignKeyConstraint(["license_id"], ["llm_license.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_data_human_id"), "llm_data", ["human_id"], unique=True)
    # ### end Alembic commands ###

    # start custom
    # inject parsed legacy 'models.json' data into db
    inject_llms_data()
    # end custom


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_llm_data_human_id"), table_name="llm_data")
    op.drop_table("llm_data")
    op.drop_table("llm_license")
    op.drop_table("llm_lab")
    op.drop_index(op.f("ix_llm_endpoint_name"), table_name="llm_endpoint")
    op.drop_table("llm_endpoint")
    # ### end Alembic commands ###
