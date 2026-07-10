import uuid
from typing import Annotated

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
    updated_at: AutoDatetime
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="auth_user.id")
