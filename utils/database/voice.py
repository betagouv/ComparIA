import uuid
from datetime import datetime

from sqlmodel import select

from backend.config import settings
from utils.database.models.llms import LLMEndpoint
from utils.database.models.voice import (
    DEFAULT_MODELS,
    VoiceRecording,
    VoiceSettings,
)
from utils.database.session import get_session
from utils.storage.redis import (
    REDIS_VOICE_SETTINGS_KEY,
    invalidate_cache,
    redis_cache,
)

# Used before the migration has run and when there is no database at all, so
# the admin panel and the arena see the same shape either way.
_DEFAULT = VoiceSettings(id=1, models=list(DEFAULT_MODELS))


@redis_cache(REDIS_VOICE_SETTINGS_KEY)
async def get_voice_settings() -> VoiceSettings:
    if not settings.COMPARIA_DB_URI:
        return _DEFAULT
    async with get_session() as session:
        return await session.get(VoiceSettings, 1) or _DEFAULT


async def get_voice_endpoint(voice: VoiceSettings) -> LLMEndpoint | None:
    """The endpoint voice input transcribes through, or None to fall back to
    the environment. Not cached with the settings: the key lives on the
    endpoint, and an operator rotating it in the LLM admin must take effect."""
    if not voice.endpoint_id or not settings.COMPARIA_DB_URI:
        return None
    async with get_session() as session:
        return await session.get(LLMEndpoint, voice.endpoint_id)


async def list_voice_endpoints() -> list[LLMEndpoint]:
    """Every endpoint an admin could point voice input at."""
    if not settings.COMPARIA_DB_URI:
        return []
    async with get_session() as session:
        result = await session.exec(select(LLMEndpoint).order_by(LLMEndpoint.name))
        return list(result.all())


async def update_voice_settings(patch: dict, updated_by: uuid.UUID) -> VoiceSettings:
    async with get_session() as session:
        row = await session.get(VoiceSettings, 1)
        if not row:
            row = VoiceSettings(id=1, models=list(DEFAULT_MODELS))

        for key, value in patch.items():
            setattr(row, key, value)
        row.updated_at = datetime.now()
        row.updated_by = updated_by

        session.add(row)
        await session.commit()
        await session.refresh(row)

    invalidate_cache(REDIS_VOICE_SETTINGS_KEY)
    return row


async def save_recording(recording: VoiceRecording) -> VoiceRecording:
    async with get_session() as session:
        session.add(recording)
        await session.commit()
        await session.refresh(recording)

    return recording


async def attach_recordings(recording_ids: list[uuid.UUID], turn_id: uuid.UUID) -> None:
    """Point recordings at the turn their text ended up in.

    Ids come from the browser, so a row already attached to another turn is left
    alone rather than moved: replaying a request must not steal someone's
    recording.
    """
    if not recording_ids:
        return

    async with get_session() as session:
        for recording_id in recording_ids:
            recording = await session.get(VoiceRecording, recording_id)
            if recording and recording.turn_id is None:
                recording.turn_id = turn_id
                session.add(recording)
        await session.commit()
