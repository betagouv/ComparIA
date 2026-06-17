import uuid
from datetime import datetime
from typing import Annotated

from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlmodel import Field

ModelId = Annotated[uuid.UUID, Field(default_factory=uuid.uuid4, primary_key=True)]
AutoDatetime = Annotated[
    datetime, Field(default_factory=datetime.now, sa_type=TIMESTAMP)
]
OptionalDatetime = Annotated[datetime | None, Field(sa_type=TIMESTAMP)]
RequiredDatetime = Annotated[datetime, Field(sa_type=TIMESTAMP)]
