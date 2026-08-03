"""
Unit tests for publish destination config validation (no DB).

Run with pytest, or directly:
    uv run python tests/database/test_publish_destination.py
"""

import os
import sys
import uuid
from pathlib import Path

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from utils.database.models import (  # noqa: E402
    AdminPublishDestination,
    PublishDestination,
    PublishDestinationUpsert,
)


def test_kind_comes_from_the_config():
    hf = PublishDestinationUpsert.model_validate(
        {
            "name": "Hugging Face",
            "config": {
                "kind": "huggingface",
                "repo_path": "org/comparia",
                "token": "t",
            },
            "datasets": ["normal"],
        }
    )
    assert hf.config.kind == "huggingface"

    s3 = PublishDestinationUpsert.model_validate(
        {
            "name": "Bucket",
            "config": {
                "kind": "s3",
                "endpoint": "s3.example.org",
                "bucket": "datasets",
                "access_key": "a",
                "secret_key": "b",
            },
            "datasets": ["raw"],
        }
    )
    assert s3.config.kind == "s3"
    assert s3.config.prefix == ""


def rejects(payload: dict) -> bool:
    try:
        PublishDestinationUpsert.model_validate(payload)
    except ValidationError:
        return True
    return False


def test_bad_configs_are_refused():
    base = {"name": "x", "datasets": ["normal"]}
    hf = {"kind": "huggingface", "token": "t"}
    # A repo path that is not 'organisation/repository' fails at the first push,
    # in the middle of the night, which is what this check exists to prevent.
    assert rejects({**base, "config": {**hf, "repo_path": "comparia"}})
    assert rejects({**base, "config": {**hf, "repo_path": "org/a/b"}})
    assert rejects({**base, "config": {**hf, "repo_path": ""}})
    # Hugging Face settings under an S3 kind, and the other way round.
    assert rejects({**base, "config": {"kind": "s3", "repo_path": "org/comparia"}})
    assert rejects({**base, "config": {"kind": "ftp", "repo_path": "org/comparia"}})
    # minio takes a host, not a URL.
    assert rejects(
        {
            **base,
            "config": {
                "kind": "s3",
                "endpoint": "https://s3.example.org",
                "bucket": "b",
                "access_key": "a",
                "secret_key": "b",
            },
        }
    )
    # A destination that receives nothing, or the same dataset twice.
    assert rejects({"name": "x", "datasets": [], "config": {**hf, "repo_path": "o/r"}})
    assert rejects(
        {"name": "x", "datasets": ["raw", "raw"], "config": {**hf, "repo_path": "o/r"}}
    )
    assert rejects(
        {"name": "x", "datasets": ["everything"], "config": {**hf, "repo_path": "o/r"}}
    )


def test_credentials_stay_in_the_backend():
    row = PublishDestination(
        id=uuid.uuid4(),
        name="Hugging Face",
        kind="huggingface",
        config={"kind": "huggingface", "repo_path": "org/comparia", "token": "secret"},
        datasets=["normal"],
        enabled=True,
    )
    assert row.parsed_config().token == "secret"

    admin = AdminPublishDestination.from_row(row)
    assert "secret" not in admin.model_dump_json()

    row.kind = "s3"
    row.config = {
        "kind": "s3",
        "endpoint": "s3.example.org",
        "bucket": "datasets",
        "access_key": "public-ish",
        "secret_key": "secret",
    }
    assert "secret" not in AdminPublishDestination.from_row(row).model_dump_json()


if __name__ == "__main__":
    test_kind_comes_from_the_config()
    test_bad_configs_are_refused()
    test_credentials_stay_in_the_backend()
    print("ok")
