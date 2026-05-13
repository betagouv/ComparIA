import uuid
from typing import Annotated

from sqlmodel import Field

ModelId = Annotated[uuid.UUID, Field(default_factory=uuid.uuid4, primary_key=True)]
