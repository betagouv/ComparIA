"""
The decision model migration's seeds: an English or Danish instance gets the
same criteria as a French one, in its own words.
"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from utils.database.models.prompt_check import PromptCheckCriterion  # noqa: E402

migration = importlib.import_module(
    "utils.database.alembic.versions."
    "d7e2a9c4b1f8_move_prompt_checks_to_a_decision_model"
)

WORDS = {"label", "question", "yes", "no"}


@pytest.mark.parametrize("locale", sorted(migration.CRITERIA_TEXTS))
def test_every_criterion_is_translated(locale):
    texts = migration.CRITERIA_TEXTS[locale]

    assert set(texts) == {criterion["key"] for criterion in migration.CRITERIA}
    for key, words in texts.items():
        assert set(words) == WORDS, key
        assert all(words.values()), key


@pytest.mark.parametrize("locale", sorted(migration.CRITERIA_TEXTS))
def test_a_translation_changes_only_the_words(locale):
    texts = migration.CRITERIA_TEXTS[locale]

    for criterion in migration.CRITERIA:
        seeded = {**criterion, **texts[criterion["key"]]}
        PromptCheckCriterion.model_validate(seeded)
        assert {k: v for k, v in seeded.items() if k not in WORDS} == {
            k: v for k, v in criterion.items() if k not in WORDS
        }
        # The model reads the text as `message`: every question names it.
        assert "`message`" in seeded["question"]
