"""
Unit tests for sending a built dataset to destinations (no network, no DB).

    uv run pytest tests/dataset/test_publish.py
"""

import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from utils.database.models.publish import PublishDestination  # noqa: E402
from utils.dataset import publish as publish_module  # noqa: E402
from utils.dataset.publish import (  # noqa: E402
    LOCAL_NAMES,
    DestinationError,
    _hf_repo,
    publish,
)


def destination(name: str, config: dict, datasets: list[str]) -> PublishDestination:
    return PublishDestination(
        id=uuid.uuid4(),
        name=name,
        kind=config["kind"],
        config=config,
        datasets=datasets,
        enabled=True,
    )


HF = {"kind": "huggingface", "repo_path": "org/comparia", "token": "t"}
S3 = {
    "kind": "s3",
    "endpoint": "s3.example.org",
    "bucket": "datasets",
    "access_key": "a",
    "secret_key": "b",
}


def test_the_raw_dataset_goes_to_its_own_repository():
    config = destination("hf", HF, ["normal"]).parsed_config()
    assert _hf_repo(config, "normal") == "org/comparia"
    assert _hf_repo(config, "raw") == "org/comparia-raw"


def record(sent: list, kind: str):
    def push(config, dataset, build_dir):
        sent.append((kind, dataset, build_dir.name))

    return push


def test_each_destination_gets_the_datasets_it_asked_for(monkeypatch):
    sent: list = []
    monkeypatch.setattr(publish_module, "_push_to_huggingface", record(sent, "hf"))
    monkeypatch.setattr(publish_module, "_push_to_s3", record(sent, "s3"))

    built = {
        "normal": Path("/build") / LOCAL_NAMES["normal"],
        "raw": Path("/build") / LOCAL_NAMES["raw"],
    }
    publish(
        [
            destination("open", HF, ["normal"]),
            destination("private bucket", S3, ["normal", "raw"]),
        ],
        built,
    )

    assert sent == [
        ("hf", "normal", "comparisons"),
        ("s3", "normal", "comparisons"),
        ("s3", "raw", "comparisons-raw"),
    ]


def test_a_dataset_that_was_not_built_is_skipped(monkeypatch):
    sent: list = []
    monkeypatch.setattr(publish_module, "_push_to_huggingface", record(sent, "hf"))

    publish(
        [destination("open", HF, ["normal", "raw"])],
        {"normal": Path("/build") / LOCAL_NAMES["normal"]},
    )
    assert sent == [("hf", "normal", "comparisons")]


def test_one_destination_failing_does_not_hide_the_others(monkeypatch):
    sent: list = []

    def broken(config, dataset, build_dir):
        raise RuntimeError("401")

    monkeypatch.setattr(publish_module, "_push_to_huggingface", broken)
    monkeypatch.setattr(publish_module, "_push_to_s3", record(sent, "s3"))

    try:
        publish(
            [
                destination("open", HF, ["normal"]),
                destination("bucket", S3, ["normal"]),
            ],
            {"normal": Path("/build") / LOCAL_NAMES["normal"]},
        )
    except DestinationError as exc:
        assert "open (normal): 401" in str(exc)
    else:
        raise AssertionError("expected the run to fail")

    # The bucket still received its copy before the run was declared failed.
    assert sent == [("s3", "normal", "comparisons")]
