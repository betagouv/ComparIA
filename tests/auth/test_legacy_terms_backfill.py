"""
Unit test for the terms backfill in the consent migration (no DB).

Run with pytest, or directly:
    uv run python tests/auth/test_legacy_terms_backfill.py
"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class Operations:
    """Records what the migration asks for instead of touching a database."""

    def __init__(self):
        self.comparison_column = None
        self.executed_sql = ""
        self.altered_column = None
        self.indexes = []

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None

    def add_column(self, table, column):
        if table == "comparison":
            self.comparison_column = column

    def execute(self, statement):
        self.executed_sql = str(statement)

    def create_index(self, name, table, columns, **kwargs):
        self.indexes.append(name)

    def alter_column(self, table, column, **kwargs):
        if table == "comparison":
            self.altered_column = (column, kwargs)


def test_past_comparisons_keep_an_honest_terms_attribution():
    migration = importlib.import_module(
        "utils.database.alembic.versions.d4f9a1c7e2b8_add_auditable_consent_records"
    )
    operations = Operations()
    original = migration.op
    migration.op = operations
    try:
        migration.upgrade()
    finally:
        migration.op = original

    assert operations.comparison_column.server_default.arg == "legacy-pre-versioning"
    assert "consent.terms_version" in operations.executed_sql
    assert "'legacy-'" in operations.executed_sql
    assert (
        "consent.consented_at <= comparison_row.created_at" in operations.executed_sql
    )
    assert "comparison_row.user_id IS NOT NULL" in operations.executed_sql
    assert "ix_auth_consent_log_user_id_consented_at" in operations.indexes
    assert operations.altered_column == (
        "participation_terms_version",
        {"nullable": False},
    )


if __name__ == "__main__":
    test_past_comparisons_keep_an_honest_terms_attribution()
