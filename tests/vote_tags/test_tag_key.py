"""
Tests for the slug a custom vote tag gets on creation.

The key is what a vote stores and what the dataset publishes, and it never
changes afterwards, so getting it from the label is worth pinning down.

DB-free. Runnable either way:
    uv run python tests/vote_tags/test_tag_key.py
    pytest tests/vote_tags/test_tag_key.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from backend.vote_tags.services import _tag_key  # noqa: E402
from utils.database.models.vote_tag import RESERVED_KEYS  # noqa: E402


def test_accents_and_spaces_become_a_plain_slug():
    assert _tag_key("Bien sourcée") == "bien_sourcee"
    assert _tag_key("Trop lente à répondre") == "trop_lente_a_repondre"
    assert _tag_key("Réponse  très   claire") == "reponse_tres_claire"


def test_punctuation_collapses_and_never_hangs_off_the_ends():
    assert _tag_key("  Clear formatting!  ") == "clear_formatting"
    assert _tag_key("A/B testing") == "a_b_testing"
    assert _tag_key("--edge--") == "edge"


def test_a_label_with_nothing_to_slug_gives_an_empty_key():
    # The service turns this into a 422 rather than storing a blank key.
    for label in ("!!!", "???", "   ", "…"):
        assert _tag_key(label) == ""


def test_the_key_fits_the_column():
    assert len(_tag_key("mot " * 60)) <= 100


def test_the_shipped_keys_are_what_the_slug_would_produce():
    # Not a rule the code enforces, but if it ever stopped holding the seeded
    # rows and freshly created ones would follow different conventions.
    for key in RESERVED_KEYS:
        assert _tag_key(key.replace("_", " ")) == key


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
            print(f"ok  {name}")
    print("all good")
