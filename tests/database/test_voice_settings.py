"""
Unit tests for the voice settings model (no DB).

Pytest-free: collects under pytest AND runs directly with
    uv run python tests/database/test_voice_settings.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.database.models.voice import (
    DEFAULT_MODELS,
    VoiceSettings,
    VoiceSettingsPatch,
    validate_models,
)


def rejects(value) -> bool:
    try:
        validate_models(value)
    except ValueError:
        return True
    return False


def test_seeded_off_with_a_pool():
    voice = VoiceSettings()
    assert voice.enabled is False
    assert voice.store_audio is False
    assert voice.models == list(DEFAULT_MODELS)
    # Off means off: nothing should run before an admin says so.
    assert voice.should_run is False


def test_an_empty_pool_never_runs():
    assert VoiceSettings(enabled=True, models=[]).should_run is False
    assert VoiceSettings(enabled=True, models=["speech/one"]).should_run is True


def test_models_are_trimmed_and_kept_in_order():
    assert validate_models([" a/one ", "b/two"]) == ["a/one", "b/two"]


def test_bad_pools_are_refused():
    assert rejects([])
    assert rejects("a/one")
    assert rejects(["a/one", "a/one"])
    assert rejects(["a/one", ""])
    assert rejects(["a/one", 3])


def test_patch_only_carries_what_was_set():
    patch = VoiceSettingsPatch(enabled=True).validated()
    assert patch == {"enabled": True}


def test_patch_validates_the_pool():
    assert VoiceSettingsPatch(models=[" x/y "]).validated() == {"models": ["x/y"]}
    try:
        VoiceSettingsPatch(models=[]).validated()
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_max_seconds_is_bounded():
    for value in (0, 4, 3600):
        try:
            VoiceSettingsPatch(max_seconds=value)
            raised = False
        except ValueError:
            raised = True
        assert raised, value


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
