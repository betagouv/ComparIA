from pydantic import BaseModel, Field, RootModel, ValidationError, model_validator
from pydantic_core import PydanticCustomError
from typing import Any, Literal, Tuple, get_args, Annotated


class License(BaseModel):
    license: str
    license_desc: str
    distribution: Literal["api-only", "open-weights", "fully-open-source"]
    reuse: bool
    commercial_use: bool | None = None
    reuse_specificities: str | None = None
    commercial_use_specificities: str | None = None


class Endpoint(BaseModel):
    api_type: str | None = "openai"
    api_base: str | None = None
    api_model_id: str


class Model(BaseModel):
    new: bool = False
    status: Literal["archived", "missing_data", "disabled", "enabled"] | None = (
        "enabled"
    )
    id: str
    simple_name: str
    license: str
    fully_open_source: bool | None = None
    release_date: str = Field(pattern=r"^[0-9]{2}/[0-9]{4}$")
    params: int | float | Literal["XS", "S", "M", "L", "XL"]
    active_params: int | float | None = None
    arch: str
    reasoning: bool | Literal["hybrid"] = False
    quantization: Literal["q4", "q8"] | None = None
    url: str | None = None  # FIXME required?
    endpoint: Endpoint | None = None
    desc: str
    size_desc: str
    fyi: str

    @model_validator(mode="after")
    def check_endpoint(self):
        if self.status == "enabled" and not self.endpoint:
            raise PydanticCustomError(
                "endpoint", "Model is enabled but no endpoint has been found."
            )
        return self


class Organisation(BaseModel):
    name: str
    icon_path: str | None = None  # FIXME required?
    proprietary_license_desc: str | None = None
    proprietary_reuse: bool = False
    proprietary_commercial_use: bool | None = None
    proprietary_reuse_specificities: str | None = None
    proprietary_commercial_use_specificities: str | None = None
    models: list[Model]


Licenses = RootModel[list[License]]
Orgas = RootModel[list[Organisation]]
