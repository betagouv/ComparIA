import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_existing_comparisons_receive_honest_terms_attribution():
    migration = importlib.import_module(
        "utils.database.alembic.versions.e4a8c2d9f1b7_add_versioned_legal_documents"
    )

    class Operations:
        added_column = None
        executed_sql = ""
        altered_column = None
        created_indexes = []

        def __getattr__(self, _name):
            return lambda *args, **kwargs: None

        def add_column(self, table, column):
            if table == "comparison":
                self.added_column = column

        def execute(self, statement):
            self.executed_sql = str(statement)

        def create_index(self, name, table, columns, **kwargs):
            self.created_indexes.append((name, table, columns, kwargs))

        def alter_column(self, table, column, **kwargs):
            if table == "comparison":
                self.altered_column = (column, kwargs)

    operations = Operations()
    original_operations = migration.op
    migration.op = operations
    try:
        migration.upgrade()
    finally:
        migration.op = original_operations

    assert operations.added_column.server_default.arg == "legacy-pre-versioning"
    assert "CONCAT" in operations.executed_sql
    assert "'legacy-'" in operations.executed_sql
    assert "consent.terms_version" in operations.executed_sql
    assert (
        "consent.consented_at <= comparison_row.created_at" in operations.executed_sql
    )
    assert "comparison_row.user_id IS NOT NULL" in operations.executed_sql
    assert any(
        name == "ix_auth_consent_log_user_id_consented_at"
        for name, *_ in operations.created_indexes
    )
    assert operations.altered_column == (
        "participation_terms_version",
        {"nullable": False},
    )


if __name__ == "__main__":
    test_existing_comparisons_receive_honest_terms_attribution()
