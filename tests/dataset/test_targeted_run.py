"""The scheduler and manual action must target exactly one destination."""

import asyncio
import os
import uuid

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from backend import publishing


def test_run_export_passes_the_destination_to_the_child(monkeypatch):
    destination_id = uuid.uuid4()
    captured: tuple = ()

    class Process:
        pid = 42

        async def wait(self):
            return 0

    async def create_process(*args, **kwargs):
        nonlocal captured
        captured = args
        return Process()

    monkeypatch.setattr(publishing.asyncio, "create_subprocess_exec", create_process)

    asyncio.run(publishing.run_export(destination_id))

    assert captured[-2:] == ("--destination-id", str(destination_id))
