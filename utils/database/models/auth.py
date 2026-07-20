import uuid
from datetime import datetime
from typing import Annotated, Literal

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel, String

from .utils import AutoDatetime, Datetime, ModelId, OptionalDatetime

UserId = Annotated[uuid.UUID, Field(foreign_key="auth_user.id")]

UserRole = Literal["user", "admin"]
LegalDocumentKind = Literal["terms", "privacy_policy"]
ConsentPurpose = Literal["terms_and_participation", "research_data_sharing"]


class User(SQLModel, table=True):
    __tablename__ = "auth_user"

    id: ModelId
    email: str = Field(unique=True)
    role: Annotated[UserRole, Field(sa_type=String)] = "user"
    created_at: AutoDatetime
    last_seen_at: AutoDatetime
    deleted_at: OptionalDatetime = None

    login_codes: list["LoginCode"] = Relationship(back_populates="user")
    auth_sessions: list["AuthSession"] = Relationship(back_populates="user")
    consent_logs: list["ConsentLog"] = Relationship(back_populates="user")


class UserPublic(SQLModel):
    id: uuid.UUID
    email: str
    role: UserRole
    created_at: str
    last_seen_at: str
    source: str


class LoginCode(SQLModel, table=True):
    __tablename__ = "auth_login_code"

    id: ModelId
    user_id: UserId
    code_hash: str
    created_at: AutoDatetime
    expires_at: Datetime
    used_at: OptionalDatetime = None

    user: User | None = Relationship(back_populates="login_codes")


class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_session"

    id: ModelId
    user_id: UserId
    token_hash: str = Field(index=True)
    created_at: AutoDatetime
    expires_at: Datetime
    revoked_at: OptionalDatetime = None
    user_agent: str | None = None
    ip: str

    user: User | None = Relationship(back_populates="auth_sessions")


class InviteToken(SQLModel, table=True):
    __tablename__ = "auth_invite_token"

    id: ModelId
    user_id: UserId
    invited_by: UserId
    token_hash: str = Field(index=True)
    created_at: AutoDatetime
    expires_at: Datetime
    used_at: OptionalDatetime = None


class LegalDocument(SQLModel, table=True):
    """An immutable published legal document.

    A corrected document must be published under a new version. Consent records
    retain both the foreign key and the digest so the accepted text remains
    independently auditable.
    """

    __tablename__ = "legal_document"
    __table_args__ = (
        UniqueConstraint(
            "kind", "version", "language", name="uq_legal_document_version"
        ),
    )

    id: ModelId
    kind: Annotated[LegalDocumentKind, Field(sa_type=String)]
    version: str
    language: str
    content: str
    content_hash: str = Field(index=True, min_length=64, max_length=64)
    published_at: AutoDatetime
    effective_at: Datetime
    retired_at: OptionalDatetime = None


class ConsentLog(SQLModel, table=True):
    __tablename__ = "auth_consent_log"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source_anonymous_consent_id",
            name="uq_auth_consent_log_source_anonymous",
        ),
    )

    id: ModelId
    user_id: UserId
    terms_version: str
    document_id: uuid.UUID | None = Field(default=None, foreign_key="legal_document.id")
    document_hash: str | None = Field(default=None, max_length=64)
    auth_session_id: uuid.UUID | None = Field(
        default=None, foreign_key="auth_session.id"
    )
    source_anonymous_consent_id: uuid.UUID | None = Field(
        default=None, foreign_key="anonymous_consent_log.id"
    )
    language: str | None = Field(default=None, max_length=16)
    purpose: Annotated[ConsentPurpose, Field(sa_type=String)] = (
        "terms_and_participation"
    )
    client_accepted_at: datetime | None = Field(default=None)
    consented_at: AutoDatetime
    associated_at: OptionalDatetime = None
    ip: str
    withdrawn_at: OptionalDatetime = None

    user: User | None = Relationship(back_populates="consent_logs")


class AnonymousConsentLog(SQLModel, table=True):
    __tablename__ = "anonymous_consent_log"

    id: ModelId
    anonymous_user_hash: str = Field(index=True, min_length=64, max_length=64)
    document_id: uuid.UUID = Field(foreign_key="legal_document.id")
    terms_version: str
    document_hash: str = Field(min_length=64, max_length=64)
    language: str = Field(max_length=16)
    purpose: Annotated[ConsentPurpose, Field(sa_type=String)]
    client_accepted_at: datetime
    consented_at: AutoDatetime
    withdrawn_at: OptionalDatetime = None
