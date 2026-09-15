from typing import Annotated

from sqlmodel import Field, String

from utils.validation import NonEmptyStr

from ..utils import BaseDBModel
from .constants import LLMLicenseKind

FIELDS = {
    "kind": {"title": "Licence type"},
    "name": {"description": "Licence name (e.g. 'Apache 2.0' or 'MIT')."},
    "reuse": {"title": "Allows reuse/redistribution."},
    "commercial_use": {"title": "Allows commercial use."},
}


class LLMLicenseBase(BaseDBModel):
    kind: Annotated[LLMLicenseKind, Field(sa_type=String, **FIELDS["kind"])]
    name: Annotated[NonEmptyStr, Field(**FIELDS["name"])]
    reuse: Annotated[bool, Field(**FIELDS["reuse"])]
    commercial_use: Annotated[bool, Field(**FIELDS["commercial_use"])]


class LLMLicense(LLMLicenseBase, table=True):
    """
    LLM licence metadata.
    """

    __tablename__ = "llm_license"


class LLMLicenseUpsert(LLMLicenseBase):
    pass


class LLMLicensePublic(LLMLicenseBase):
    pass
