"""
Voice input: a microphone in the prompt box, transcribed by a speech model.

The speech model is picked at random from a pool on every recording, so the pool
is compared on real traffic without anyone being asked to vote. What makes that
a measurement rather than a guess is keeping three things together: the
recording, the text the speech model produced, and the prompt the user finally
sent. The distance between the last two says how good the model was.

Storage is off by default, and with it off no row is written at all: the
transcription lives in the browser until the user sends it, and the database
records a prompt like any other. See docs/adr/0004-voice-input-transcription.md.
"""

import uuid
from typing import Annotated

from sqlalchemy import LargeBinary
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from .utils import AutoDatetime, ModelId

# Models exposed by POST https://openrouter.ai/api/v1/audio/transcriptions.
# Seeded rather than fetched: the endpoint lists models an instance may not want
# to send audio to, so the pool is a decision an admin makes, not a list we
# import wholesale.
DEFAULT_MODELS = (
    "mistralai/voxtral-mini-transcribe",
    "nvidia/parakeet-tdt-0.6b-v3",
    "openai/gpt-4o-mini-transcribe",
    "deepgram/nova-3",
)

# What MediaRecorder produces in every browser that matters, and what the
# transcription endpoint accepts without a transcode.
AUDIO_CONTENT_TYPE = "audio/webm"

DEFAULT_MAX_SECONDS = 60
# Upstream providers cut a transcription off after 60 seconds of processing.
# A recording longer than this is one we would pay for and not get back.
MAX_SECONDS_LIMIT = 300

# Roughly ten minutes of webm/opus, so it refuses a file that is not a recording
# rather than a recording that is merely long.
MAX_AUDIO_BYTES = 5 * 1024 * 1024


def validate_models(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("Models must be a list")

    result: list[str] = []
    for model in value:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Every model must be a non-empty string")
        model = model.strip()
        if model in result:
            raise ValueError(f"Duplicate model '{model}'")
        result.append(model)

    if not result:
        raise ValueError("At least one model is needed")
    return result


class VoiceSettings(SQLModel, table=True):
    """Singleton row (id=1) holding the voice input configuration."""

    __tablename__ = "voice_settings"

    id: int = Field(default=1, primary_key=True)
    enabled: bool = Field(
        default=False,
        description="Show a microphone in the prompt box.",
    )
    # Separate from `enabled` on purpose. An instance can offer the microphone
    # without keeping anything, which is the only way to run this feature where
    # storing a voice is not acceptable.
    store_audio: bool = Field(
        default=False,
        description=(
            "Keep the recording, the transcription and the model that produced "
            "it. With this off nothing is stored and model rotation teaches "
            "nothing, so a pool of one is the honest configuration."
        ),
    )
    models: Annotated[
        list[str],
        Field(
            sa_type=JSONB,
            description=(
                "Speech models to draw from, one picked at random per recording."
            ),
        ),
    ] = list(DEFAULT_MODELS)
    # Overrides OPENROUTER_API_KEY when set, as prompt_check.api_key does.
    # Never leaves the backend.
    api_key: str | None = Field(default=None)
    max_seconds: int = Field(
        default=DEFAULT_MAX_SECONDS,
        ge=5,
        le=MAX_SECONDS_LIMIT,
        description="Recording stops itself after this many seconds.",
    )
    # Null means keep forever, which is the default. The column exists from the
    # first migration so that deciding on a retention later needs no schema
    # change, not because anything purges yet.
    retention_days: int | None = Field(default=None, ge=1)
    updated_at: AutoDatetime
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="auth_user.id")

    @property
    def should_run(self) -> bool:
        return self.enabled and bool(self.models)


class VoiceSettingsPublic(SQLModel):
    enabled: bool
    store_audio: bool
    models: list[str]
    # Whether a key is stored, never the key itself.
    has_api_key: bool
    max_seconds: int
    retention_days: int | None = None
    updated_at: str
    updated_by: uuid.UUID | None = None


class VoiceSettingsPatch(SQLModel):
    enabled: bool | None = None
    store_audio: bool | None = None
    models: list[str] | None = None
    # Write-only. An empty string clears the stored key and falls back to the
    # environment variable.
    api_key: str | None = None
    max_seconds: int | None = Field(default=None, ge=5, le=MAX_SECONDS_LIMIT)
    retention_days: int | None = Field(default=None, ge=1)

    def validated(self) -> dict:
        patch = self.model_dump(exclude_unset=True)
        if patch.get("models") is not None:
            patch["models"] = validate_models(patch["models"])
        return patch


class VoiceRecording(SQLModel, table=True):
    """One recording, its transcription, and the turn it ended up in.

    A null `turn_id` is an unused recording: the visitor deleted the
    transcription instead of sending it. Those are kept, because a
    transcription someone threw away says as much about a speech model as one
    they accepted.
    """

    __tablename__ = "voice_recording"

    id: ModelId
    created_at: AutoDatetime
    turn_id: uuid.UUID | None = Field(
        default=None, foreign_key="turn.id", ondelete="CASCADE"
    )

    audio: Annotated[bytes, Field(sa_type=LargeBinary)]
    content_type: str = AUDIO_CONTENT_TYPE
    duration_ms: int
    model: str
    transcription: str
    locale: str
    latency_ms: int
