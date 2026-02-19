import json
from pathlib import Path
from types import NoneType, UnionType
from typing import Any, Literal, Union, get_args, get_origin

from pydantic.fields import FieldInfo

from utils.utils import write_json

from ..archs import Arch, Archs
from ..licenses import Distribution, License, Licenses
from ..llms import Endpoint, LLMDataRawBase
from ..organisations import RawOrganisation, RawOrgas

CURRENT_DIR = Path(__file__).parent

LICENSES_SCHEMA_FILE = CURRENT_DIR / "schema-licenses.json"
ARCHS_SCHEMA_FILE = CURRENT_DIR / "schema-archs.json"
ORGAS_SCHEMA_FILE = CURRENT_DIR / "schema-organisations.json"
MD_BASE_FILE = CURRENT_DIR / "README.md"
MD_OUTPUT_FILE = CURRENT_DIR.parent / "README.md"

# TODO check archs and licenses for generating a proper literal


def get_anno_repr(anno: type[Any] | None) -> str:
    origin = get_origin(anno)
    if origin in (UnionType, Union, Literal):
        return " | ".join(
            [get_anno_repr(arg) for arg in get_args(anno) if arg is not NoneType]
        )

    return anno.__name__ if anno and not isinstance(anno, str) else f"`'{anno}'`"


def get_model_doc(fields: dict[str, FieldInfo]) -> str:
    def is_required(field: FieldInfo) -> bool:
        origin = get_origin(field.annotation)
        return origin is None or (
            origin is UnionType and NoneType not in get_args(field.annotation)
        )

    return "  \n".join(
        [
            f"- `{name}`: {get_anno_repr(field.annotation)} {'(optional)' if not is_required(field) else ''} *{field.description}*"
            for name, field in fields.items()
        ]
    )


def main():
    """
    For each models, generate a JSON schema and retrieve attributes infos to build a doc
    """
    # LLMs
    base_empty_llm_def = LLMDataRawBase.model_construct(
        new=True,
        id="",
        simple_name="",
        license="",
        release_date="MM/YYYY",
        arch="",
        params=None,
        endpoint=Endpoint.model_construct(),
        desc="",
        size_desc="",
        fyi="",
    ).model_dump()

    # Organisations
    base_empty_orga_def = RawOrganisation.model_construct(
        name="",
        icon_path="",
        models=[],
    ).model_dump()
    orga_schema = RawOrgas.model_json_schema()
    write_json(ORGAS_SCHEMA_FILE, orga_schema)

    # Licenses
    base_empty_licence_def = License.model_construct(
        license="",
        license_desc="",
        distribution="|".join(get_args(Distribution)),
        reuse=False,
    ).model_dump()
    write_json(LICENSES_SCHEMA_FILE, Licenses.model_json_schema())

    # Architectures
    base_empty_arch_def = Arch.model_construct(
        id="", name="", title="", desc=""
    ).model_dump()
    write_json(ARCHS_SCHEMA_FILE, Archs.model_json_schema())

    # Fill base markdown doc
    MD_OUTPUT_FILE.write_text(
        MD_BASE_FILE.read_text().format(
            orga=json.dumps(base_empty_orga_def, indent=2),
            orga_attrs=get_model_doc(RawOrganisation.model_fields),
            llm=json.dumps(base_empty_llm_def, indent=2),
            llm_attrs=get_model_doc(LLMDataRawBase.model_fields),
            license_attrs=get_model_doc(License.model_fields),
            license=json.dumps(base_empty_licence_def, indent=2),
            arch=json.dumps(base_empty_arch_def, indent=2),
            arch_attrs=get_model_doc(Arch.model_fields),
        )
    )


if __name__ == "__main__":
    main()
