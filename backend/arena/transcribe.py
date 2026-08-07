"""
Turning a recording into text, with a speech model drawn at random from the
pool an admin configured.

The rotation is the point. Nobody is asked to vote on a transcription: over
enough recordings the pool is compared on real traffic, by keeping the audio,
the text the model produced and the prompt the user finally sent. That only
happens where the admin turned storage on. With it off nothing is written and
the transcription is the browser's business alone.

Called directly rather than through LiteLLM, which does not support OpenRouter
for transcription (BerriAI/litellm#27083).
"""

import base64
import logging
import random
import time
from typing import TYPE_CHECKING, Final

import httpx
import sentry_sdk

from backend.config import settings
from utils.database.models.voice import (
    AUDIO_CONTENT_TYPE,
    VoiceRecording,
    VoiceSettings,
)
from utils.database.voice import get_voice_settings, save_recording

if TYPE_CHECKING:
    from fastapi import Request

logger = logging.getLogger("languia")

TRANSCRIPTION_URL: Final[str] = "https://openrouter.ai/api/v1/audio/transcriptions"
# Upstream providers cut a transcription off at 60 seconds of processing, so
# waiting longer than that only holds a worker open on a request already lost.
TRANSCRIPTION_TIMEOUT: Final[float] = 60.0

# The `format` the endpoint expects for what MediaRecorder produces. Opus is the
# codec inside the container, not a format the API names.
AUDIO_FORMAT: Final[str] = "webm"


class TranscriptionError(RuntimeError):
    """Raised when no text came back, whatever the reason."""


async def transcribe(audio: bytes, model: str, api_key: str, language: str) -> str:
    """Send one recording to OpenRouter and return the text it produced."""
    async with httpx.AsyncClient(timeout=TRANSCRIPTION_TIMEOUT) as client:
        response = await client.post(
            TRANSCRIPTION_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "input_audio": {
                    "data": base64.b64encode(audio).decode(),
                    "format": AUDIO_FORMAT,
                },
                "language": language,
            },
        )
        response.raise_for_status()
        payload = response.json()

    return str(payload.get("text") or "").strip()


def pick_model(voice: VoiceSettings) -> str:
    return random.choice(voice.models)


async def run_transcription(
    audio: bytes,
    duration_ms: int,
    locale: str,
    request: "Request | None" = None,
) -> tuple[str, VoiceRecording | None]:
    """
    Transcribe a recording, and keep it when the instance says to.

    Returns the text and the stored row, or None in place of the row when
    `store_audio` is off, in which case nothing about this recording is written
    down: the text goes back to the browser and lives there until the user sends
    it, indistinguishable from something typed.
    """
    voice = await get_voice_settings()
    if not voice.should_run:
        raise TranscriptionError("Voice input is disabled")

    api_key = voice.api_key or settings.OPENROUTER_API_KEY
    if not api_key:
        raise TranscriptionError("No API key configured")

    model = pick_model(voice)
    started = time.monotonic()
    try:
        text = await transcribe(audio, model, api_key, locale)
    except Exception as e:
        logger.error(f"transcription_failed: {model}: {e}", extra={"request": request})
        if settings.SENTRY_DSN:
            sentry_sdk.capture_exception(e)
        raise TranscriptionError(str(e)) from e

    latency_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        f"transcription: model={model} latency_ms={latency_ms} chars={len(text)}",
        extra={"request": request},
    )

    if not voice.store_audio:
        return text, None

    recording = await save_recording(
        VoiceRecording(
            audio=audio,
            content_type=AUDIO_CONTENT_TYPE,
            duration_ms=duration_ms,
            model=model,
            transcription=text,
            locale=locale,
            latency_ms=latency_ms,
        )
    )
    return text, recording
