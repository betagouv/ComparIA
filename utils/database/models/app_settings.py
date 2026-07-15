import uuid
from typing import Annotated, Literal

from sqlalchemy import LargeBinary
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from .utils import AutoDatetime


class AppSettings(SQLModel, table=True):
    """Singleton row (id=1) holding product settings editable from the admin panel."""

    __tablename__ = "app_settings"

    id: int = Field(default=1, primary_key=True)
    auth_access_policy: str = Field(default="anonymous_first")
    auth_domain_allowlist: Annotated[list[str], Field(sa_type=JSONB)] = []
    votes_objective: int = Field(default=300_000)
    platform_name: str = Field(default="Compar:IA")
    logo: Annotated[bytes | None, Field(sa_type=LargeBinary)] = None
    logo_content_type: str | None = None
    updated_at: AutoDatetime
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="auth_user.id")


class AppSettingsPublic(SQLModel):
    auth_access_policy: Literal["anonymous_first", "sign_in_required"]
    auth_domain_allowlist: list[str]
    votes_objective: int
    platform_name: str
    has_custom_logo: bool
    updated_at: str
    updated_by: uuid.UUID | None = None


class AppSettingsPatch(SQLModel):
    auth_access_policy: Literal["anonymous_first", "sign_in_required"] | None = None
    auth_domain_allowlist: list[str] | None = None
    votes_objective: int | None = None
    platform_name: str | None = None
