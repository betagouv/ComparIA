from typing import Annotated

from sqlmodel import Field, String

from ..utils import BaseDBModel
from .constants import LLMLicenseKind


class LLMLicenseBase(BaseDBModel):
    kind: Annotated[LLMLicenseKind, Field(sa_type=String)]
    name: str
    reuse: bool
    commercial_use: bool


class LLMLicense(LLMLicenseBase, table=True):
    """
    LLM licence metadata.

    Attributes
    ----------
    kind
        Licence type.
    name
        Licence name (e.g. 'Apache 2.0' or 'MIT').
    reuse
        Whether the licence allows reuse/redistribution.
    commercial_use
        Whether the licence allows commercial use.
    """

    __tablename__ = "llm_license"


class LLMLicensePublic(LLMLicenseBase):
    pass
