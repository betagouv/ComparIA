import pytest
from pydantic import ValidationError

from utils.database.models.prompt_check import (
    DEFAULT_THRESHOLDS,
    MISTRAL_CATEGORIES,
    NEVER_BLOCK,
    PromptCheck,
    PromptCheckPatch,
)


def test_seeded_thresholds_only_use_real_categories():
    for thresholds in DEFAULT_THRESHOLDS.values():
        assert set(thresholds) <= set(MISTRAL_CATEGORIES)
        assert not set(thresholds) & set(NEVER_BLOCK)


def test_sexual_threshold_catches_the_minor_case():
    """Mistral has no minor category and scored an explicit request involving a
    12-year-old at 0.41, so the default must sit below that."""
    assert DEFAULT_THRESHOLDS["content_safety"]["sexual"] <= 0.41


def test_blocking_categories_uses_per_category_thresholds():
    check = PromptCheck(
        kind="content_safety", thresholds={"sexual": 0.3, "criminal": 0.9}
    )
    assert check.blocking_categories({"sexual": 0.41, "criminal": 0.5}) == ["sexual"]
    assert check.blocking_categories({"sexual": 0.41, "criminal": 0.95}) == [
        "criminal",
        "sexual",
    ]
    assert check.blocking_categories({"sexual": 0.1}) == []


def test_missing_score_does_not_block():
    check = PromptCheck(kind="pii", thresholds={"pii": 0.5})
    assert check.blocking_categories({}) == []


@pytest.mark.parametrize(
    "thresholds",
    [
        {"health": 0.5},
        {"law": 0.9},
        {"financial": 0.1},
    ],
)
def test_never_block_categories_are_rejected(thresholds):
    with pytest.raises(ValidationError):
        PromptCheckPatch(thresholds=thresholds)


def test_unknown_category_is_rejected():
    with pytest.raises(ValidationError):
        PromptCheckPatch(thresholds={"toxicity": 0.5})


@pytest.mark.parametrize("threshold", [-0.1, 1.1, "high", True])
def test_out_of_range_threshold_is_rejected(threshold):
    with pytest.raises(ValidationError):
        PromptCheckPatch(thresholds={"sexual": threshold})


def test_valid_patch_coerces_to_float():
    patch = PromptCheckPatch(mode="block", thresholds={"sexual": 0, "criminal": 1})
    assert patch.thresholds == {"sexual": 0.0, "criminal": 1.0}


def test_invalid_mode_is_rejected():
    with pytest.raises(ValidationError):
        PromptCheckPatch(mode="warn_and_pray")
