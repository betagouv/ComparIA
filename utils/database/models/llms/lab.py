from ..utils import BaseDBModel


class LLMLabBase(BaseDBModel):
    name: str
    logo: str  # icon name, or file?
    origin_country: str  # FIXME use lib?


class LLMLab(LLMLabBase, table=True):
    """
    LLM lab/organization metadata.

    Attributes
    ----------
    name
        Lab name.
    logo
        An icon name from https://lobehub.com/fr/icons or a filename
        (e.g. 'ai2.svg') from `frontend/static/orgs/ai/`.
    origin_country
        Lab's origin country as a 2 letter code from https://en.wikipedia.org/wiki/ISO_3166-1.
    """

    __tablename__ = "llm_lab"


class LLMLabPublic(LLMLabBase):
    pass
