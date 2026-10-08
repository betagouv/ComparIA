"""
What a comparison is allowed to tell the browser before the vote is in.

The arena is blind: until the user has chosen, nothing in the payload may name
either model. Run with pytest, or directly:
    uv run python tests/database/test_comparison_public.py
"""

import os
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import utils.database.models.comparison as comparison_model  # noqa: E402
from utils.database.models import (  # noqa: E402
    ComparisonPublic,
    ErrorDetails,
    LLMMessageCreate,
)

SYSTEM_PROMPT = "Tu es Mistral Large, un assistant francais."


def public(revealed: bool) -> ComparisonPublic:
    # The reveal payload itself is computed elsewhere and tested elsewhere.
    original = comparison_model.get_reveal_data
    comparison_model.get_reveal_data = lambda _comparison, _llms: None
    try:
        return ComparisonPublic.model_validate(
            {
                "id": uuid4(),
                "mode": "random",
                "custom_models_selection": None,
                "error": None,
                "turns": [],
                "revealed": revealed,
                "reveal_data": None,
                "llm_id_a": uuid4(),
                "llm_id_b": uuid4(),
                "system_msg_a": SYSTEM_PROMPT,
                "system_msg_b": "Tu es un assistant.",
            },
            context={"llms_data": None},
        )
    finally:
        comparison_model.get_reveal_data = original


def test_the_model_ids_are_withheld_before_the_vote():
    comparison = public(revealed=False)

    assert comparison.llm_id_a is None
    assert comparison.llm_id_b is None


def test_the_system_prompts_are_withheld_before_the_vote():
    """A system prompt written for one model usually names it, so sending it
    while withholding the id gives the answer away anyway."""
    comparison = public(revealed=False)

    assert comparison.system_msg_a is None
    assert comparison.system_msg_b is None
    assert SYSTEM_PROMPT not in comparison.model_dump_json()


def test_a_revealed_comparison_keeps_everything():
    comparison = public(revealed=True)

    assert comparison.llm_id_a is not None
    assert comparison.system_msg_a == SYSTEM_PROMPT


def test_the_provider_fingerprints_never_reach_the_browser():
    """The generation id carries the provider's own id prefix, and the token
    count and cache hit differ per model. All three stay server-side."""
    message = LLMMessageCreate(
        content="Bonjour", generation_id="gen-01ab", tokens=42, is_cached=True
    )

    sent = message.model_dump()

    assert "generation_id" not in sent
    assert "tokens" not in sent
    assert "is_cached" not in sent
    # Still set on the object, because the row saved afterwards needs them.
    assert message.generation_id == "gen-01ab"


def test_an_error_written_before_the_codes_still_loads():
    """Rows already in the table hold the raw provider message and no code."""
    error = ErrorDetails.model_validate(
        {"message": "litellm.APIError: OpenAI... ", "pos": "a", "is_timeout": False}
    )

    assert error.code is None
    assert error.pos == "a"


def run():
    test_the_model_ids_are_withheld_before_the_vote()
    test_the_system_prompts_are_withheld_before_the_vote()
    test_a_revealed_comparison_keeps_everything()
    test_the_provider_fingerprints_never_reach_the_browser()
    test_an_error_written_before_the_codes_still_loads()
    print("Comparison blinding cases passed.")


if __name__ == "__main__":
    run()
