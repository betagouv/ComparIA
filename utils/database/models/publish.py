import re
import uuid
from datetime import datetime
from typing import Annotated, Literal, get_args

from pydantic import Field as PydanticField
from pydantic import TypeAdapter, field_validator
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, String

from utils.validation import NonEmptyStr

from .utils import BaseDBModel, Datetime, OptionalDatetime

# The two datasets a run produces. Code, not configuration: a destination picks
# which of them it receives, it cannot invent a third.
PublishDataset = Literal["normal", "raw"]
PUBLISH_DATASETS: tuple[PublishDataset, ...] = get_args(PublishDataset)

PublishKind = Literal["huggingface", "s3"]

# How often a destination publishes. The execution time is deliberately fixed;
# administrators only choose the frequency.
PublishFrequency = Literal["off", "daily", "weekly", "monthly"]
PUBLISH_FREQUENCIES: tuple[PublishFrequency, ...] = get_args(PublishFrequency)

# What HF_PUSH_DATASET_PATH had to look like: '{organisation}/{repo_prefix}'.
_REPO_PATH = re.compile(r"^[\w.-]+/[\w.-]+$")


class HuggingFaceConfigPublic(SQLModel):
    kind: Literal["huggingface"] = "huggingface"
    # The raw dataset is pushed to '{repo_path}-raw'.
    repo_path: NonEmptyStr

    @field_validator("repo_path")
    @classmethod
    def valid_repo_path(cls, value: str) -> str:
        if not _REPO_PATH.match(value):
            raise ValueError("repo path has to look like 'organisation/repository'")
        return value


class HuggingFaceConfig(HuggingFaceConfigPublic):
    token: NonEmptyStr


class HuggingFaceConfigInput(HuggingFaceConfigPublic):
    token: NonEmptyStr | None = None


class S3ConfigPublic(SQLModel):
    kind: Literal["s3"] = "s3"
    # Host and optional port, no scheme: what minio expects.
    endpoint: NonEmptyStr
    bucket: NonEmptyStr
    region: NonEmptyStr | None = None
    # Prepended to every uploaded key, so one bucket can hold several instances.
    prefix: str = ""
    secure: bool = True

    @field_validator("endpoint")
    @classmethod
    def without_scheme(cls, value: str) -> str:
        if "://" in value:
            raise ValueError("endpoint is a host, without 'https://'")
        return value


class S3Config(S3ConfigPublic):
    access_key: NonEmptyStr
    secret_key: NonEmptyStr


class S3ConfigInput(S3ConfigPublic):
    access_key: NonEmptyStr | None = None
    secret_key: NonEmptyStr | None = None


PublishConfig = Annotated[
    HuggingFaceConfig | S3Config, PydanticField(discriminator="kind")
]
PublishConfigPublic = Annotated[
    HuggingFaceConfigPublic | S3ConfigPublic, PydanticField(discriminator="kind")
]
PublishConfigInput = Annotated[
    HuggingFaceConfigInput | S3ConfigInput, PydanticField(discriminator="kind")
]

_CONFIG: TypeAdapter[HuggingFaceConfig | S3Config] = TypeAdapter(PublishConfig)
_CONFIG_PUBLIC: TypeAdapter[HuggingFaceConfigPublic | S3ConfigPublic] = TypeAdapter(
    PublishConfigPublic
)

# The fields the admin panel never shows back, so an administrator editing a
# destination cannot retype them. Left empty, they keep the stored value.
SECRET_FIELDS: dict[PublishKind, tuple[str, ...]] = {
    "huggingface": ("token",),
    "s3": ("access_key", "secret_key"),
}


class MissingSecretError(ValueError):
    def __init__(self, field: str):
        self.field = field
        super().__init__(f"'{field}' is required")


def config_to_store(
    incoming: HuggingFaceConfigInput | S3ConfigInput, stored: dict | None = None
) -> dict:
    """
    The config to write, with the secrets the panel left blank filled in from
    the row being edited. Nothing is carried over when the kind changes: the
    new kind's secrets have to be given.
    """
    config = incoming.model_dump()
    keep = stored if stored and stored.get("kind") == incoming.kind else {}
    for field in SECRET_FIELDS[incoming.kind]:
        value = config.get(field) or keep.get(field)
        if not value:
            raise MissingSecretError(field)
        config[field] = value
    return config


class PublishDestinationBase(BaseDBModel):
    name: Annotated[NonEmptyStr, Field(max_length=100)]
    kind: Annotated[PublishKind, Field(sa_type=String)]
    # Credentials live here in plain text, like LLMEndpoint.api_key, and never
    # leave the backend: the admin API answers with the Public config models.
    config: Annotated[dict, Field(sa_type=JSONB)]
    # Which datasets this destination receives. Naming them per destination is
    # what lets an instance put the open dataset on a public repository and the
    # raw one, which still holds the flagged comparisons, somewhere private.
    datasets: Annotated[list[str], Field(sa_type=JSONB)]
    enabled: bool = Field(default=True)
    publish_frequency: Annotated[PublishFrequency, Field(sa_type=String)] = "off"


class PublishDestination(PublishDestinationBase, table=True):
    __tablename__ = "publish_destination"

    def parsed_config(self) -> HuggingFaceConfig | S3Config:
        return _CONFIG.validate_python(self.config)


class PublishDestinationUpsert(SQLModel):
    """
    'kind' is not sent: it is read off the config, so a row cannot end up
    claiming one kind and holding the other's settings.
    """

    name: NonEmptyStr
    config: PublishConfigInput
    datasets: list[PublishDataset]
    enabled: bool = True
    publish_frequency: PublishFrequency = "off"

    @field_validator("datasets")
    @classmethod
    def at_least_one_dataset(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("a destination needs at least one dataset")
        if len(set(value)) != len(value):
            raise ValueError("a dataset can only be listed once")
        return value


class AdminPublishDestination(SQLModel):
    id: uuid.UUID
    name: str
    kind: PublishKind
    config: PublishConfigPublic
    datasets: list[PublishDataset]
    enabled: bool
    publish_frequency: PublishFrequency
    next_run_at: datetime | None = None

    @classmethod
    def from_row(cls, row: PublishDestination) -> "AdminPublishDestination":
        return cls(
            id=row.id,
            name=row.name,
            kind=row.kind,
            config=_CONFIG_PUBLIC.validate_python(row.config),
            datasets=row.datasets,  # type: ignore[arg-type]
            enabled=row.enabled,
            publish_frequency=row.publish_frequency,
        )


class AdminPublishDestinationsResponse(SQLModel):
    destinations: list[AdminPublishDestination]


class PublishRun(BaseDBModel, table=True):
    """
    One pass over the whole database. An instance only ever looks at the last
    one, but a row per run costs nothing and answers 'when did this start
    failing'.
    """

    __tablename__ = "publish_run"

    started_at: Datetime
    finished_at: OptionalDatetime = None
    # None while the run is going, then whether it finished.
    succeeded: bool | None = None
    error: str | None = None
    # What the open dataset carried, and what analysis kept out of it. Both are
    # null for a run that did not rebuild the open dataset. A held-back share
    # that jumps from two percent to forty is the alarm that the analysis
    # model, or its configuration, broke.
    held_back: int | None = None
    published: int | None = None


class AdminPublishRun(SQLModel):
    started_at: datetime
    finished_at: datetime | None
    succeeded: bool | None
    error: str | None
    held_back: int | None
    published: int | None


class AdminPublishStatus(SQLModel):
    # Shared across destinations: a run says what was published, while each
    # destination owns only its schedule.
    runs: list[AdminPublishRun]
