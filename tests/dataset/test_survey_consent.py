"""
Unit tests for the consent gate on survey answers in the dataset export.

Run with pytest, or directly:
    uv run python tests/dataset/test_survey_consent.py

No DB: the rule is tested as a pure function and the SQL it produces is
inspected to confirm the consent gate (and the published/archived filters)
are applied at the query.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from utils.database.models import LEGACY_PARTICIPATION_TERMS_VERSION  # noqa: E402
from utils.dataset import compute  # noqa: E402


def test_current_terms_version_is_publishable():
    assert compute.publishable_survey_terms_versions("2026.07") == {"2026.07"}


def test_legacy_marker_is_not_publishable():
    # "legacy-pre-versioning" is stamped when NO terms document was published:
    # nothing was accepted, so nothing may be published.
    assert (
        LEGACY_PARTICIPATION_TERMS_VERSION
        not in compute.publishable_survey_terms_versions("2026.07")
    )


def test_null_terms_version_is_not_publishable():
    # Old rows predate version recording; no proof of consent, so exclude.
    assert compute.publishable_survey_terms_versions(None) == set()


def _compiled_sql(active_version: str | None) -> str:
    statement = compute._survey_answers_query(
        compute.publishable_survey_terms_versions(active_version)
    )
    return str(statement.compile(compile_kwargs={"literal_binds": True}))


def test_query_filters_on_the_active_version():
    sql = _compiled_sql("2026.07")
    assert "terms_version IN ('2026.07')" in sql


def test_query_excludes_null_and_legacy_versions():
    sql = _compiled_sql("2026.07")
    assert LEGACY_PARTICIPATION_TERMS_VERSION not in sql
    # NULL terms_version can't match an IN list, so old rows are excluded too.


def test_query_with_no_active_version_admits_nothing():
    sql = _compiled_sql(None)
    assert "terms_version IN (NULL)" in sql


def test_query_still_excludes_unpublished_and_archived_questions():
    sql = _compiled_sql("2026.07")
    assert "published" in sql
    assert "archived_at IS NULL" in sql


if __name__ == "__main__":
    test_current_terms_version_is_publishable()
    test_legacy_marker_is_not_publishable()
    test_null_terms_version_is_not_publishable()
    test_query_filters_on_the_active_version()
    test_query_excludes_null_and_legacy_versions()
    test_query_with_no_active_version_admits_nothing()
    test_query_still_excludes_unpublished_and_archived_questions()
