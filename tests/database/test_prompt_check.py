import pytest
from pydantic import ValidationError

from utils.database.models.prompt_check import (
    DEFAULT_CRITERIA,
    MAX_CRITERIA,
    PromptCheck,
    PromptCheckUpsert,
)


def criterion(key: str, action: str = "log", threshold: float = 0.5, **rest) -> dict:
    return {
        "key": key,
        "label": key.title(),
        "question": f"Is the `message` about {key}?",
        "threshold": threshold,
        "action": action,
        **rest,
    }


def make_check(*criteria: dict) -> PromptCheck:
    return PromptCheck(criteria=list(criteria))


def seeded(key: str) -> dict:
    return next(c for c in DEFAULT_CRITERIA if c["key"] == key)


def test_seeded_criteria_are_valid():
    assert PromptCheckUpsert(criteria=DEFAULT_CRITERIA).criteria is not None


def test_a_fresh_install_acts_rather_than_watches():
    """An instance nobody has configured still refuses attempts to get round
    the rules and asks before sending sexual or self-harm content."""
    assert seeded("jailbreaking")["action"] == "block"
    assert seeded("sexual")["action"] == "warn"
    assert seeded("selfharm")["action"] == "warn"


def test_the_topic_criteria_still_only_watch():
    """These describe subjects people are entitled to ask about, so acting on
    them would refuse ordinary prompts."""
    for key in ("hate_and_discrimination", "violence_and_threats", "pii", "spam"):
        assert seeded(key)["action"] == "log"


def test_the_seed_names_the_right_message():
    assert seeded("selfharm")["message"] == "self_harm"
    assert seeded("pii")["message"] == "pii"


def test_triggered_maps_each_criterion_to_its_action():
    check = make_check(
        criterion("sexual", "block", 0.3), criterion("criminal", "log", 0.9)
    )
    assert check.triggered({"sexual": 0.41, "criminal": 0.5}) == {"sexual": "block"}
    assert check.triggered({"sexual": 0.41, "criminal": 0.95}) == {
        "sexual": "block",
        "criminal": "log",
    }
    assert check.triggered({"sexual": 0.1}) == {}


def test_a_score_equal_to_the_threshold_triggers():
    check = make_check(criterion("sexual", "warn", 0.3))

    assert check.triggered({"sexual": 0.3}) == {"sexual": "warn"}
    assert check.triggered({"sexual": 0.29}) == {}


def test_a_criterion_that_is_off_never_triggers_and_is_not_asked():
    check = make_check(criterion("health", "off", 0.1))

    assert check.triggered({"health": 1.0}) == {}
    assert check.action_for({"health": 1.0}) == "off"
    assert check.active_criteria == []


def test_missing_score_does_not_trigger():
    check = make_check(criterion("pii", "block"))

    assert check.triggered({}) == {}


def test_action_for_takes_the_strongest_triggered_action():
    check = make_check(
        criterion("pii", "log"),
        criterion("sexual", "warn"),
        criterion("criminal", "block"),
    )
    assert check.action_for({"pii": 0.9}) == "log"
    assert check.action_for({"pii": 0.9, "sexual": 0.9}) == "warn"
    assert check.action_for({"pii": 0.9, "sexual": 0.9, "criminal": 0.9}) == "block"
    assert check.action_for({}) == "off"


def test_should_run_only_when_a_criterion_asks_for_something():
    assert make_check().should_run is False
    assert (
        make_check(criterion("pii", "off"), criterion("law", "off")).should_run is False
    )
    assert (
        make_check(criterion("pii", "log"), criterion("law", "off")).should_run is True
    )


def test_the_switch_stops_the_check_whatever_the_criteria_say():
    check = make_check(criterion("pii", "block"))
    assert check.should_run is True

    check.enabled = False
    assert check.should_run is False


def test_an_admin_can_add_any_criterion():
    patch = PromptCheckUpsert(
        criteria=[criterion("off_topic", "block", yes="Ads", no="")]
    )

    assert patch.model_dump(exclude_unset=True)["criteria"] == [
        {
            "key": "off_topic",
            "label": "Off_Topic",
            "question": "Is the `message` about off_topic?",
            "yes": "Ads",
            "no": "",
            "threshold": 0.5,
            "action": "block",
            "message": "generic",
        }
    ]


def test_no_criteria_at_all_is_allowed():
    assert PromptCheckUpsert(criteria=[]).criteria == []


@pytest.mark.parametrize("key", ["Spam", "1spam", "spam-ads", "", "a" * 41])
def test_a_key_that_cannot_name_a_score_is_rejected(key: str):
    with pytest.raises(ValidationError, match="Key must be"):
        PromptCheckUpsert(criteria=[criterion("spam") | {"key": key}])


def test_duplicate_keys_are_rejected():
    with pytest.raises(ValidationError, match="Duplicate keys: spam"):
        PromptCheckUpsert(criteria=[criterion("spam"), criterion("spam", "block")])


def test_too_many_criteria_are_rejected():
    with pytest.raises(ValidationError, match=f"At most {MAX_CRITERIA}"):
        PromptCheckUpsert(
            criteria=[criterion(f"c{i}") for i in range(MAX_CRITERIA + 1)]
        )


@pytest.mark.parametrize("field", ["label", "question"])
def test_an_empty_label_or_question_is_rejected(field: str):
    with pytest.raises(ValidationError):
        PromptCheckUpsert(criteria=[criterion("spam") | {field: ""}])


@pytest.mark.parametrize("threshold", [-0.1, 1.1, "high", None])
def test_out_of_range_threshold_is_rejected(threshold):
    with pytest.raises(ValidationError):
        PromptCheckUpsert(criteria=[criterion("sexual", threshold=threshold)])


def test_unknown_action_or_message_is_rejected():
    with pytest.raises(ValidationError):
        PromptCheckUpsert(criteria=[criterion("sexual", "warn_and_pray")])
    with pytest.raises(ValidationError):
        PromptCheckUpsert(criteria=[criterion("sexual", message="hotline")])


def test_valid_patch_coerces_thresholds_to_float():
    patch = PromptCheckUpsert(
        criteria=[criterion("sexual", threshold=0), criterion("criminal", threshold=1)]
    )
    criteria = patch.model_dump()["criteria"]
    assert criteria[0]["threshold"] == 0.0
    assert criteria[1]["threshold"] == 1.0


def test_the_public_shape_reports_a_stored_key_without_carrying_it():
    from utils.database.models.prompt_check import PromptCheckPublic

    assert "api_key" not in PromptCheckPublic.model_fields
    assert "has_api_key" in PromptCheckPublic.model_fields


def test_a_key_can_be_written_but_never_read_back():
    from utils.database.models.prompt_check import PromptCheckPublic

    patch = PromptCheckUpsert(api_key="sk-secret")
    assert patch.api_key == "sk-secret"
    assert "api_key" not in PromptCheckPublic.model_fields
