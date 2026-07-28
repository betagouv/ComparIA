import uuid
from typing import Annotated, Literal

from sqlmodel import Field, Relationship, SQLModel, String

from .utils import AutoDatetime, Datetime, ModelId, OptionalDatetime

UserId = Annotated[uuid.UUID, Field(foreign_key="auth_user.id")]

UserRole = Literal["user", "admin"]


class UserBase(SQLModel):
    id: ModelId
    email: str = Field(unique=True)
    role: Annotated[UserRole, Field(sa_type=String)] = "user"


class User(UserBase, table=True):
    __tablename__ = "auth_user"

    created_at: AutoDatetime
    last_seen_at: AutoDatetime
    deleted_at: OptionalDatetime = None

    login_codes: list["LoginCode"] = Relationship(back_populates="user")
    auth_sessions: list["AuthSession"] = Relationship(back_populates="user")
    consent_logs: list["ConsentLog"] = Relationship(back_populates="user")


class UserUpsert(UserBase):
    pass


class UserPublic(UserBase):
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


class ConsentLog(SQLModel, table=True):
    __tablename__ = "auth_consent_log"

    id: ModelId
    user_id: UserId
    terms_version: str
    consented_at: AutoDatetime
    ip: str

    user: User | None = Relationship(back_populates="consent_logs")
