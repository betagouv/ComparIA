from pydantic import BeforeValidator


def strip_and_empty_as_none(v: str | None) -> str | None:
    v = v.strip() if v else None
    return None if not v else v


StripAndEmptyAsNone = BeforeValidator(strip_and_empty_as_none)
