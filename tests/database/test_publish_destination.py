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
from utils.database.models.publish import (  # noqa: E402
    MissingSecretError,
    config_to_store,
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


def upsert(config: dict, **kwargs) -> PublishDestinationUpsert:
    return PublishDestinationUpsert.model_validate(
        {"name": "x", "datasets": ["normal"], "config": config, **kwargs}
    )


def test_a_blank_secret_keeps_the_stored_one():
    stored = {"kind": "huggingface", "repo_path": "org/comparia", "token": "secret"}
    edited = upsert({"kind": "huggingface", "repo_path": "org/other"})

    config = config_to_store(edited.config, stored)
    assert config["token"] == "secret"
    assert config["repo_path"] == "org/other"

    replaced = upsert({"kind": "huggingface", "repo_path": "org/other", "token": "new"})
    assert config_to_store(replaced.config, stored)["token"] == "new"


def test_a_secret_is_required_when_there_is_nothing_to_keep():
    hf = upsert({"kind": "huggingface", "repo_path": "org/comparia"})
    for stored in (
        None,
        # Nothing carries over when the kind changes: an S3 row holds no token.
        {"kind": "s3", "access_key": "a", "secret_key": "b"},
    ):
        try:
            config_to_store(hf.config, stored)
        except MissingSecretError as exc:
            assert exc.field == "token"
        else:
            raise AssertionError("expected a missing token")

    s3 = upsert({"kind": "s3", "endpoint": "s3.example.org", "bucket": "b"})
    try:
        config_to_store(s3.config, None)
    except MissingSecretError as exc:
        assert exc.field == "access_key"
    else:
        raise AssertionError("expected a missing access key")


if __name__ == "__main__":
    test_kind_comes_from_the_config()
    test_bad_configs_are_refused()
    test_credentials_stay_in_the_backend()
    test_a_blank_secret_keeps_the_stored_one()
    test_a_secret_is_required_when_there_is_nothing_to_keep()
    print("ok")
