"""
Unit tests for voice transcription (mocked HTTP, no DB, no real Redis).

Pytest-free: collects under pytest AND runs directly with
    uv run python tests/arena/test_transcribe.py
"""

import asyncio
import base64
import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import httpx

import backend.arena.transcribe as transcribe
from backend.config import settings
from utils.database.models.voice import VoiceSettings

AUDIO = b"fake-webm-bytes"


class FakeProvider:
    """Records every transcription request and replays a canned text."""

    def __init__(self, text="bonjour docteur", error=None):
        self.text = text
        self.error = error
        self.requests: list[dict] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        if self.error:
            raise self.error
        return httpx.Response(200, json={"text": self.text})


@contextlib.contextmanager
def arena(voice, text="bonjour docteur", error=None):
    fake = FakeProvider(text, error)
    saved: list[object] = []
    orig_client = transcribe.httpx.AsyncClient
    orig_load = transcribe.get_voice_settings
    orig_save = transcribe.save_recording
    orig_key = settings.OPENROUTER_API_KEY

    async def get_voice_settings():
        return voice

    async def save_recording(recording):
        saved.append(recording)
        return recording

    transcribe.httpx.AsyncClient = lambda **kwargs: orig_client(
        transport=httpx.MockTransport(fake.handler), **kwargs
    )
    transcribe.get_voice_settings = get_voice_settings
    transcribe.save_recording = save_recording
    settings.OPENROUTER_API_KEY = "test-key"
    try:
        yield fake, saved
    finally:
        transcribe.httpx.AsyncClient = orig_client
        transcribe.get_voice_settings = orig_load
        transcribe.save_recording = orig_save
        settings.OPENROUTER_API_KEY = orig_key


def config(**kwargs):
    kwargs.setdefault("enabled", True)
    kwargs.setdefault("models", ["speech/one"])
    return VoiceSettings(id=1, **kwargs)


def run(voice, text="bonjour docteur", error=None, locale="fr"):
    with arena(voice, text, error) as (fake, saved):
        try:
            result = asyncio.run(transcribe.run_transcription(AUDIO, 4200, locale))
        except transcribe.TranscriptionError as e:
            result = e
    return result, fake, saved


def test_disabled_makes_no_call():
    result, fake, saved = run(config(enabled=False))
    assert isinstance(result, transcribe.TranscriptionError)
    assert fake.requests == []
    assert saved == []


def test_empty_pool_makes_no_call():
    result, fake, _ = run(config(models=[]))
    assert isinstance(result, transcribe.TranscriptionError)
    assert fake.requests == []


def test_audio_is_sent_as_webm_with_the_locale():
    (text, recording), fake, _ = run(config(), locale="da")
    assert text == "bonjour docteur"
    assert recording is None

    sent = fake.requests[0]
    assert sent["model"] == "speech/one"
    assert sent["language"] == "da"
    assert sent["input_audio"]["format"] == "webm"
    assert base64.b64decode(sent["input_audio"]["data"]) == AUDIO


def test_nothing_is_stored_when_store_audio_is_off():
    (_, recording), _, saved = run(config(store_audio=False))
    assert recording is None
    assert saved == []


def test_storing_keeps_the_audio_and_which_model_ran():
    (_, recording), _, saved = run(config(store_audio=True), text="deux mots")

    assert len(saved) == 1
    assert recording is saved[0]
    assert recording.audio == AUDIO
    assert recording.content_type == "audio/webm"
    assert recording.transcription == "deux mots"
    assert recording.model == "speech/one"
    assert recording.duration_ms == 4200
    # Unattached until the prompt it ends up in is sent.
    assert recording.turn_id is None


def test_provider_failure_raises_and_stores_nothing():
    result, _, saved = run(
        config(store_audio=True), error=httpx.ConnectError("no route")
    )
    assert isinstance(result, transcribe.TranscriptionError)
    assert saved == []


def test_model_is_drawn_from_the_whole_pool():
    voice = config(models=["speech/one", "speech/two", "speech/three"])
    picked = {transcribe.pick_model(voice) for _ in range(200)}
    assert picked == set(voice.models)


def test_no_api_key_makes_no_call():
    with arena(config()) as (fake, _):
        settings.OPENROUTER_API_KEY = None
        try:
            asyncio.run(transcribe.run_transcription(AUDIO, 1000, "fr"))
            raised = False
        except transcribe.TranscriptionError:
            raised = True
    assert raised
    assert fake.requests == []


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok {name}")
