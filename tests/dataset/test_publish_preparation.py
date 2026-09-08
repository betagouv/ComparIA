"""Publication prepares open data before building it."""

import asyncio
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from utils.database import lint as lint_module
from utils.dataset import run


def exercise_export(monkeypatch, tmp_path, datasets):
    events: list[str] = []
    destination_id = uuid.uuid4()
    destination = SimpleNamespace(datasets=datasets)

    async def destinations(**kwargs):
        assert kwargs == {"destination_id": destination_id}
        return [destination]

    async def prepare(**kwargs):
        assert kwargs == {"fix": True, "with_llm_analyze": True}
        events.append("prepare")

    async def build(requested, *args, **kwargs):
        events.append("build")
        return {dataset: tmp_path for dataset in requested}

    monkeypatch.setattr(run, "enabled_destinations", destinations)
    monkeypatch.setattr(lint_module, "lint", prepare)
    monkeypatch.setattr(run, "check_free_disk", lambda path: None)
    monkeypatch.setattr(run, "process_datasets", build)
    monkeypatch.setattr(run, "publish", lambda *args: events.append("publish"))

    asyncio.run(
        run._export(
            datasets,
            tmp_path,
            dry_run=False,
            use_cache=False,
            destination_id=destination_id,
        )
    )
    return events


def test_open_publication_prepares_before_building(monkeypatch, tmp_path):
    assert exercise_export(monkeypatch, tmp_path, ["normal"]) == [
        "prepare",
        "build",
        "publish",
    ]


def test_raw_only_publication_skips_analysis(monkeypatch, tmp_path):
    assert exercise_export(monkeypatch, tmp_path, ["raw"]) == ["build", "publish"]
