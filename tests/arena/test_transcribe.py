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
from utils.database.models.llms import LLMEndpoint
from utils.database.models.voice import VoiceSettings

AUDIO = b"fake-webm-bytes"


class FakeProvider:
    """Records every transcription request and replays a canned text."""

    def __init__(self, text="bonjour docteur", error=None):
        self.text = text
        self.error = error
        self.requests: list[dict] = []
        self.urls: list[str] = []
        self.raw: list[bytes] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.urls.append(str(request.url))
        self.raw.append(request.content)
        content_type = request.headers.get("content-type", "")
        # Multipart is not worth parsing here: the tests that use it check the
        # url and that the audio went out at all.
        self.requests.append(
            json.loads(request.content) if "json" in content_type else {}
        )
        if self.error:
            raise self.error
        return httpx.Response(200, json={"text": self.text})


@contextlib.contextmanager
def arena(voice, text="bonjour docteur", error=None, endpoint=None):
    fake = FakeProvider(text, error)
    saved: list[object] = []
    originals = {
        name: getattr(transcribe, name)
        for name in ("get_voice_settings", "get_voice_endpoint", "save_recording")
    }
    orig_client = transcribe.httpx.AsyncClient
    orig_key = settings.OPENROUTER_API_KEY

    async def get_voice_settings():
        return voice

    async def get_voice_endpoint(_voice):
        return endpoint

    async def save_recording(recording):
        saved.append(recording)
        return recording

    transcribe.httpx.AsyncClient = lambda **kwargs: orig_client(
        transport=httpx.MockTransport(fake.handler), **kwargs
    )
    transcribe.get_voice_settings = get_voice_settings
    transcribe.get_voice_endpoint = get_voice_endpoint
    transcribe.save_recording = save_recording
    settings.OPENROUTER_API_KEY = "test-key"
    try:
        yield fake, saved
    finally:
        transcribe.httpx.AsyncClient = orig_client
        for name, value in originals.items():
            setattr(transcribe, name, value)
        settings.OPENROUTER_API_KEY = orig_key


def config(**kwargs):
    kwargs.setdefault("enabled", True)
    kwargs.setdefault("models", ["speech/one"])
    return VoiceSettings(id=1, **kwargs)


def run(voice, text="bonjour docteur", error=None, locale="fr", endpoint=None):
    with arena(voice, text, error, endpoint) as (fake, saved):
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


def test_an_endpoint_supplies_the_url_the_key_and_the_shape():
    """An OpenAI-compatible endpoint gets the file as multipart, not base64."""
    endpoint = LLMEndpoint(
        name="Albert",
        api_type="openai",
        api_base="https://albert.example.org/v1/",
        api_key="albert-key",
    )
    (text, _), fake, _ = run(config(), endpoint=endpoint)

    assert text == "bonjour docteur"
    assert fake.urls[0] == "https://albert.example.org/v1/audio/transcriptions"
    # The audio itself, not a base64 rendering of it.
    assert AUDIO in fake.raw[0]
    assert b"speech/one" in fake.raw[0]


def test_an_openrouter_endpoint_keeps_the_base64_shape():
    endpoint = LLMEndpoint(
        name="OpenRouter", api_type="openrouter", api_key="router-key"
    )
    _, fake, _ = run(config(), endpoint=endpoint)

    assert fake.urls[0] == "https://openrouter.ai/api/v1/audio/transcriptions"
    assert base64.b64decode(fake.requests[0]["input_audio"]["data"]) == AUDIO


def test_an_endpoint_that_cannot_transcribe_is_refused():
    endpoint = LLMEndpoint(
        name="Hugging Face", api_type="huggingface", api_key="hf-key"
    )
    result, fake, _ = run(config(), endpoint=endpoint)

    assert isinstance(result, transcribe.TranscriptionError)
    assert fake.requests == []


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
