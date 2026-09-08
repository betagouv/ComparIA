"""The copy of their own data an account holder can ask for.

Built from the database rather than from whatever the open page happens to
hold, so the consent history is in it and the conversations are the stored
ones rather than the ones already fetched.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlmodel import col, select

from backend.config import TurnChoice
from utils.database.models.auth import ConsentLog, User
from utils.database.models.comparison import Comparison
from utils.database.models.llms import LLMData
from utils.database.models.turn import Turn
from utils.database.models.utils import utc_now
from utils.database.session import get_session

EXPORT_SCHEMA_VERSION = 1


class ExportedAccount(BaseModel):
    email: str
    created_at: datetime


class ExportedConsent(BaseModel):
    terms_version: str
    document_hash: str | None
    locale: str | None
    purpose: str
    accepted_at: datetime


class ExportedMessage(BaseModel):
    content: str
    created_at: datetime | None


class ExportedTurn(BaseModel):
    id: uuid.UUID
    created_at: datetime
    prompt: str
    response_a: ExportedMessage | None
    response_b: ExportedMessage | None
    choice: TurnChoice | None
    keyword_annotations_a: list[str]
    keyword_annotations_b: list[str]
    custom_annotation_a: str | None
    custom_annotation_b: str | None


class ExportedConversation(BaseModel):
    id: uuid.UUID
    created_at: datetime
    mode: str
    revealed: bool
    accepted_terms_version: str
    system_prompt_a: str | None
    system_prompt_b: str | None
    model_a: str | None
    model_b: str | None
    turns: list[ExportedTurn]


class AccountDataExport(BaseModel):
    schema_version: int = EXPORT_SCHEMA_VERSION
    exported_at: datetime
    account: ExportedAccount
    consents: list[ExportedConsent]
    conversations: list[ExportedConversation]


def _message(message) -> ExportedMessage | None:
    if not message:
        return None
    return ExportedMessage(content=message.content, created_at=message.created_at)


def _turn(turn: Turn) -> ExportedTurn:
    return ExportedTurn(
        id=turn.id,
        created_at=turn.created_at,
        prompt=turn.user_msg.content,
        response_a=_message(turn.llm_msg_a),
        response_b=_message(turn.llm_msg_b),
        choice=turn.choice,
        keyword_annotations_a=list(turn.keyword_annotations_a),
        keyword_annotations_b=list(turn.keyword_annotations_b),
        custom_annotation_a=turn.custom_annotation_a,
        custom_annotation_b=turn.custom_annotation_b,
    )


def _conversation(
    comparison: Comparison, model_names: dict[uuid.UUID, str]
) -> ExportedConversation:
    # Who answered stays hidden until the comparison is revealed, here as in
    # the arena.
    revealed = comparison.revealed
    return ExportedConversation(
        id=comparison.id,
        created_at=comparison.created_at,
        mode=comparison.mode,
        revealed=revealed,
        accepted_terms_version=comparison.participation_terms_version,
        system_prompt_a=comparison.system_msg_a,
        system_prompt_b=comparison.system_msg_b,
        model_a=model_names.get(comparison.llm_id_a) if revealed else None,
        model_b=model_names.get(comparison.llm_id_b) if revealed else None,
        turns=[_turn(turn) for turn in comparison.turns],
    )


async def build_account_export(user: User) -> AccountDataExport:
    async with get_session() as session:
        comparisons = (
            await session.exec(
                select(Comparison)
                .where(Comparison.user_id == user.id)
                .order_by(col(Comparison.created_at))
            )
        ).all()
        consents = (
            await session.exec(
                select(ConsentLog)
                .where(ConsentLog.user_id == user.id)
                .order_by(col(ConsentLog.consented_at))
            )
        ).all()
        model_names = dict(
            (await session.exec(select(LLMData.id, LLMData.human_id))).all()
        )

    return AccountDataExport(
        exported_at=utc_now(),
        account=ExportedAccount(email=user.email, created_at=user.created_at),
        consents=[
            ExportedConsent(
                terms_version=consent.terms_version,
                document_hash=consent.document_hash,
                locale=consent.language,
                purpose=consent.purpose,
                accepted_at=consent.consented_at,
            )
            for consent in consents
        ],
        conversations=[
            _conversation(comparison, model_names) for comparison in comparisons
        ],
    )
