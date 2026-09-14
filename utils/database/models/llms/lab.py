from typing import Annotated

from sqlalchemy import LargeBinary
from sqlmodel import Field

from utils.validation import NonEmptyStr

from ..utils import BaseDBModel

FIELDS = {
    "name": {},
    "logo": {
        "description": "An icon name from https://lobehub.com/fr/icons or a filename (e.g. 'ai2.svg') from `frontend/static/orgs/ai/`."
    },
    "origin_country": {
        "description": "A 2 letter code from https://en.wikipedia.org/wiki/ISO_3166-1."
    },
}


class LLMLabBase(BaseDBModel):
    name: Annotated[NonEmptyStr, Field(**FIELDS["name"])]
    logo: Annotated[NonEmptyStr, Field(**FIELDS["logo"])]  # icon name, or file?
    origin_country: Annotated[
        NonEmptyStr, Field(**FIELDS["origin_country"])
    ]  # FIXME use lib?


class LLMLab(LLMLabBase, table=True):
    """
    LLM lab/organization metadata.
    """

    __tablename__ = "llm_lab"

    logo_data: bytes | None = Field(default=None, sa_type=LargeBinary)
    logo_content_type: str | None = Field(default=None)

    @property
    def has_custom_logo(self) -> bool:
        return self.logo_data is not None


class LLMLabUpsert(LLMLabBase):
    pass


class LLMLabPublic(LLMLabBase):
    has_custom_logo: bool = False
