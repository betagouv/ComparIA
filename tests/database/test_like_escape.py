"""
Escaping of the LIKE wildcards in admin and suggestion searches.

Binding the search term stops SQL injection but not `%` and `_`, which LIKE
reads as "anything": a search for `_` used to match every row.

Run with pytest, or directly:
    uv run python tests/database/test_like_escape.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from utils.database.models.utils import escape_like  # noqa: E402


def test_the_wildcards_lose_their_meaning():
    assert escape_like("%") == "\\%"
    assert escape_like("_") == "\\_"
    assert escape_like("a%b_c") == "a\\%b\\_c"


def test_the_escape_character_itself_is_escaped():
    """Otherwise `\\%` typed by a user would escape the backslash we added and
    leave the wildcard live."""
    assert escape_like("\\") == "\\\\"
    assert escape_like("\\%") == "\\\\\\%"


def test_an_ordinary_search_is_left_alone():
    assert escape_like("marie@example.org") == "marie@example.org"


def test_the_escaped_term_is_what_the_query_carries():
    from sqlmodel import col

    from utils.database.models.auth import User

    clause = col(User.email).ilike(f"%{escape_like('a_b')}%", escape="\\")

    assert clause.compile().params["email_1"] == "%a\\_b%"


def run():
    test_the_wildcards_lose_their_meaning()
    test_the_escape_character_itself_is_escaped()
    test_an_ordinary_search_is_left_alone()
    test_the_escaped_term_is_what_the_query_carries()
    print("LIKE escaping cases passed.")


if __name__ == "__main__":
    run()
