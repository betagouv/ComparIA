import pytest
from pydantic import ValidationError

from utils.database.models.prompt_check import (
    DEFAULT_CATEGORIES,
    MISTRAL_CATEGORIES,
    OFF_BY_DEFAULT,
    PromptCheck,
    PromptCheckPatch,
)


def make_check(categories: dict[str, dict]) -> PromptCheck:
    return PromptCheck(categories=categories)


def test_seeded_categories_are_all_real_categories():
    assert set(DEFAULT_CATEGORIES) == set(MISTRAL_CATEGORIES)


def test_the_product_categories_are_seeded_off():
    """Off rather than forbidden: acting on them would refuse the very prompts a
    sante or juridique instance exists for, but an admin can still turn them on."""
    for category in OFF_BY_DEFAULT:
        assert DEFAULT_CATEGORIES[category]["action"] == "off"


def test_sexual_threshold_catches_the_minor_case():
    """Mistral has no minor category and scored an explicit request involving a
    12-year-old at 0.41, so the default must sit below that."""
    assert DEFAULT_CATEGORIES["sexual"]["threshold"] <= 0.41


def test_triggered_maps_each_category_to_its_action():
    check = make_check(
        {
            "sexual": {"threshold": 0.3, "action": "block"},
            "criminal": {"threshold": 0.9, "action": "log"},
        }
    )
    assert check.triggered({"sexual": 0.41, "criminal": 0.5}) == {"sexual": "block"}
    assert check.triggered({"sexual": 0.41, "criminal": 0.95}) == {
        "sexual": "block",
        "criminal": "log",
    }
    assert check.triggered({"sexual": 0.1}) == {}


def test_a_score_equal_to_the_threshold_triggers():
    check = make_check({"sexual": {"threshold": 0.3, "action": "warn"}})

    assert check.triggered({"sexual": 0.3}) == {"sexual": "warn"}
    assert check.triggered({"sexual": 0.29}) == {}


def test_a_category_that_is_off_never_triggers():
    check = make_check({"health": {"threshold": 0.1, "action": "off"}})

    assert check.triggered({"health": 1.0}) == {}
    assert check.action_for({"health": 1.0}) == "off"


def test_missing_score_does_not_trigger():
    check = make_check({"pii": {"threshold": 0.5, "action": "block"}})

    assert check.triggered({}) == {}


def test_action_for_takes_the_strongest_triggered_action():
    check = make_check(
        {
            "pii": {"threshold": 0.5, "action": "log"},
            "sexual": {"threshold": 0.5, "action": "warn"},
            "criminal": {"threshold": 0.5, "action": "block"},
        }
    )
    assert check.action_for({"pii": 0.9}) == "log"
    assert check.action_for({"pii": 0.9, "sexual": 0.9}) == "warn"
    assert check.action_for({"pii": 0.9, "sexual": 0.9, "criminal": 0.9}) == "block"
    assert check.action_for({}) == "off"


def test_should_run_only_when_a_category_asks_for_something():
    off = {category: {"threshold": 0.5, "action": "off"} for category in ("pii", "law")}
    assert make_check(off).should_run is False

    on = dict(off, pii={"threshold": 0.5, "action": "log"})
    assert make_check(on).should_run is True


def full_categories(**overrides: dict) -> dict[str, dict]:
    categories = {k: dict(v) for k, v in DEFAULT_CATEGORIES.items()}
    categories.update(overrides)
    return categories


@pytest.mark.parametrize("category", OFF_BY_DEFAULT)
@pytest.mark.parametrize("action", ["off", "log", "warn", "block"])
def test_every_action_is_allowed_on_the_product_categories(category: str, action: str):
    """They are seeded off, not locked. An instance that wants to block on
    finance is allowed to say so."""
    patch = PromptCheckPatch(
        categories=full_categories(**{category: {"threshold": 0.5, "action": action}})
    )
    assert patch.categories[category]["action"] == action


def test_unknown_category_is_rejected():
    with pytest.raises(ValidationError, match="Unknown category"):
        PromptCheckPatch(
            categories=full_categories(toxicity={"threshold": 0.5, "action": "log"})
        )


def test_missing_category_is_rejected():
    categories = full_categories()
    del categories["pii"]
    with pytest.raises(ValidationError, match="Missing categories"):
        PromptCheckPatch(categories=categories)


@pytest.mark.parametrize("threshold", [-0.1, 1.1, "high", True, None])
def test_out_of_range_threshold_is_rejected(threshold):
    with pytest.raises(ValidationError):
        PromptCheckPatch(
            categories=full_categories(sexual={"threshold": threshold, "action": "log"})
        )


def test_unknown_action_is_rejected():
    with pytest.raises(ValidationError, match="Unknown action"):
        PromptCheckPatch(
            categories=full_categories(
                sexual={"threshold": 0.5, "action": "warn_and_pray"}
            )
        )


def test_valid_patch_coerces_thresholds_to_float():
    patch = PromptCheckPatch(
        categories=full_categories(
            sexual={"threshold": 0, "action": "log"},
            criminal={"threshold": 1, "action": "block"},
        )
    )
    assert patch.categories["sexual"]["threshold"] == 0.0
    assert patch.categories["criminal"]["threshold"] == 1.0


def test_a_patch_may_carry_the_model_alone():
    patch = PromptCheckPatch(model="mistral-moderation-2603")

    assert patch.model_dump(exclude_unset=True) == {"model": "mistral-moderation-2603"}


def test_the_switch_stops_the_check_whatever_the_categories_say():
    check = make_check(full_categories(pii={"threshold": 0.5, "action": "block"}))
    assert check.should_run is True

    check.enabled = False
    assert check.should_run is False


def test_the_public_shape_reports_a_stored_key_without_carrying_it():
    from utils.database.models.prompt_check import PromptCheckPublic

    assert "api_key" not in PromptCheckPublic.model_fields
    assert "has_api_key" in PromptCheckPublic.model_fields


def test_a_key_can_be_written_but_never_read_back():
    from utils.database.models.prompt_check import PromptCheckPublic

    patch = PromptCheckPatch(api_key="sk-secret")
    assert patch.api_key == "sk-secret"
    assert "api_key" not in PromptCheckPublic.model_fields
