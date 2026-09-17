"""Regression tests for Grok comparison detection."""

import os
import sys
from pathlib import Path

from sqlalchemy.dialects import postgresql

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from utils.database.actions.archive_blacklisted_grok import (  # noqa: E402
    blacklisted_grok_query,
)


def test_grok_filter_uses_textual_model_ids_instead_of_uuid_foreign_keys():
    sql = str(
        blacklisted_grok_query().compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )

    assert "llm_data_1.human_id LIKE 'grok-%%'" in sql
    assert "llm_data_2.human_id LIKE 'grok-%%'" in sql
    assert "comparison.llm_id_a LIKE" not in sql
    assert "comparison.llm_id_b LIKE" not in sql
