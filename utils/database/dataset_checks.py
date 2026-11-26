import uuid
from datetime import datetime

from backend.config import settings
from utils.database.encrypted import UnreadableSecret
from utils.database.models.dataset_check import DEFAULT_CRITERIA, DatasetCheck
from utils.database.prompt_checks import get_prompt_check
from utils.database.session import get_session

# Used before the migration has run and when there is no database at all.
_DEFAULT = DatasetCheck(id=1, criteria=[dict(c) for c in DEFAULT_CRITERIA])


async def get_dataset_check() -> DatasetCheck:
    if not settings.COMPARIA_DB_URI:
        return _DEFAULT
    async with get_session() as session:
        return await session.get(DatasetCheck, 1) or _DEFAULT


async def update_dataset_check(patch: dict, updated_by: uuid.UUID) -> DatasetCheck:
    async with get_session() as session:
        row = await session.get(DatasetCheck, 1)
        if not row:
            row = DatasetCheck(id=1, criteria=[dict(c) for c in DEFAULT_CRITERIA])

        for key, value in patch.items():
            setattr(row, key, value)
        row.updated_at = datetime.now()
        row.updated_by = updated_by

        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row


async def dataset_check_api_key(
    check: DatasetCheck,
) -> str | UnreadableSecret | None:
    """The key the analysis calls with: its own, then the prompt check's, then
    OPENROUTER_API_KEY. A stored key no encryption key opens is returned as
    is, so the caller fails on it rather than quietly trying another."""
    if check.api_key:
        return check.api_key
    prompt_check = await get_prompt_check()
    return prompt_check.api_key or settings.OPENROUTER_API_KEY or None
