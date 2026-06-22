"""
Unit tests for the content-safety guardrail's pure parsing/decision logic
(no network, no DB).

Run with pytest, or directly:
    uv run python tests/arena/test_moderation.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.arena.moderation import _GENERIC, _SELF_HARM, _categories, classify


def test_safe_prompt_is_allowed():
    assert classify("User Safety: safe") is None


def test_violence_alone_is_allowed():
    assert classify("User Safety: unsafe\nSafety Categories: Violence") is None


def test_needs_caution_suppresses_block():
    assert (
        classify("User Safety: unsafe\nSafety Categories: Violence, Needs Caution")
        is None
    )


def test_egregious_categories_block():
    assert classify(
        "User Safety: unsafe\nSafety Categories: Guns and Illegal Weapons, Criminal Planning/Confessions"
    ) is _GENERIC
    assert classify(
        "User Safety: unsafe\nSafety Categories: Hate/Identity Hate, Violence"
    ) is _GENERIC
    assert classify(
        "User Safety: unsafe\nSafety Categories: Controlled/Regulated Substances"
    ) is _GENERIC
    assert classify("User Safety: unsafe\nSafety Categories: Sexual") is _GENERIC


def test_self_harm_redirects_even_with_needs_caution():
    assert (
        classify("User Safety: unsafe\nSafety Categories: Suicide and Self Harm")
        is _SELF_HARM
    )
    assert (
        classify(
            "User Safety: unsafe\nSafety Categories: Suicide and Self Harm, Needs Caution"
        )
        is _SELF_HARM
    )


def test_csam_blocks_even_with_needs_caution():
    assert classify(
        "User Safety: unsafe\nSafety Categories: Sexual (minor), Needs Caution"
    ) is _GENERIC


def test_pii_alone_is_not_blocked():
    assert classify("User Safety: unsafe\nSafety Categories: PII/Privacy") is None


def test_category_parsing():
    assert _categories("User Safety: safe") == []
    assert _categories(
        "User Safety: unsafe\nSafety Categories: Hate/Identity Hate, Violence"
    ) == ["Hate/Identity Hate", "Violence"]


def run():
    test_safe_prompt_is_allowed()
    test_violence_alone_is_allowed()
    test_needs_caution_suppresses_block()
    test_egregious_categories_block()
    test_self_harm_redirects_even_with_needs_caution()
    test_csam_blocks_even_with_needs_caution()
    test_pii_alone_is_not_blocked()
    test_category_parsing()
    print("All guardrail classify cases passed.")


if __name__ == "__main__":
    run()
