"""
Tests for the pseudonymous voter ids of the raw dataset
(utils/dataset/voters.py and their use in the export and the push).

No DB and no network:
    uv run --group data pytest tests/dataset/test_voter_ids.py
"""

import asyncio
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Patches compute's LLM lookups, so no DB is needed.
from tests.dataset.test_comparison_to_turns import (  # noqa: E402
    comparison,
    llm_msg,
    turn,
    user_msg,
)
from utils.database.models.app_settings import AppSettingsPatch  # noqa: E402
from utils.dataset import compute  # noqa: E402
from utils.dataset import publish as publish_module  # noqa: E402
from utils.dataset.publish import DestinationError  # noqa: E402
from utils.dataset.voters import VoterPseudonyms, voter_key  # noqa: E402

USER = uuid.UUID("33333333-3333-4333-8333-333333333333")
VOTERS = VoterPseudonyms(b"k" * 64)


def test_the_account_wins_over_the_anonymous_session():
    assert voter_key(USER, "hash") == (f"user:{USER}", "account")
    assert voter_key(None, "hash") == ("anon:hash", "anonymous")
    assert voter_key(None, None) is None
    assert voter_key(None, "") is None


def test_a_voter_keeps_the_same_id_and_two_voters_differ():
    first, kind = VOTERS(USER, None)
    assert kind == "account"
    assert len(first) == 32
    assert VOTERS(USER, "other-session") == (first, "account")
    assert VOTERS(uuid.uuid4(), None)[0] != first
    assert VOTERS(None, "hash")[0] != VOTERS(None, "other")[0]


def test_the_id_depends_on_the_key_and_is_not_the_internal_id():
    voter_id, _ = VOTERS(USER, None)
    assert VoterPseudonyms(b"x" * 64)(USER, None)[0] != voter_id
    assert str(USER).replace("-", "")[:32] != voter_id


def test_no_voter_no_id():
    assert VOTERS(None, None) == (None, None)


def _comparison(**owner):
    comp = comparison(
        [turn(user_msg(), llm_msg(), llm_msg(), choice="a_better")],
        llm_analyzed=True,
        contains_pii=False,
        contains_spam=False,
        archived=False,
    )
    comp.user_id = owner.get("user_id")
    comp.anonymous_user_hash = owner.get("anonymous_user_hash")
    return comp


def test_rows_carry_the_id_only_when_asked():
    comp = _comparison(anonymous_user_hash="hash")

    without = asyncio.run(compute.comparison_to_turns(comp))
    assert without[0]["extra_metadata"]["voter_id"] is None
    assert without[0]["extra_metadata"]["voter_type"] is None

    rows = asyncio.run(compute.comparison_to_turns(comp, VOTERS))
    assert rows[0]["extra_metadata"]["voter_id"] == VOTERS(None, "hash")[0]
    assert rows[0]["extra_metadata"]["voter_type"] == "anonymous"


def test_the_open_dataset_never_carries_the_id(tmp_path):
    exporters = compute._build_exporters(["normal", "raw"], tmp_path)
    rows = asyncio.run(compute.comparison_to_turns(_comparison(user_id=USER), VOTERS))
    for exporter in exporters.values():
        exporter.add_rows(rows)
        exporter.close()

    normal = pq.read_table(tmp_path / "comparisons" / "comparisons.parquet")
    raw = pq.read_table(tmp_path / "comparisons-raw" / "comparisons-raw.parquet")

    assert "extra_metadata" not in normal.column_names
    assert "voter_id" not in str(normal.schema)
    extra = raw.column("extra_metadata").to_pylist()[0]
    assert extra["voter_id"] == VOTERS(USER, None)[0]
    assert extra["voter_type"] == "account"


def _raw_build(tmp_path, voters):
    """A raw build dir, the way the export writes it."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    exporters = compute._build_exporters(["raw"], tmp_path)
    rows = asyncio.run(compute.comparison_to_turns(_comparison(user_id=USER), voters))
    exporters["raw"].add_rows(rows)
    exporters["raw"].close()
    return tmp_path / "comparisons-raw"


def test_the_send_reads_the_ids_from_the_file(tmp_path):
    assert publish_module._has_voter_ids(_raw_build(tmp_path / "with", VOTERS))
    assert not publish_module._has_voter_ids(_raw_build(tmp_path / "without", None))
    assert not publish_module._has_voter_ids(tmp_path / "nothing")


class FakeHfApi:
    def __init__(self, private: bool = False, gated=False, exists: bool = True):
        self.info = SimpleNamespace(private=private, gated=gated)
        self.exists = exists
        self.created: list[dict] = []
        self.info_calls = 0
        self.committed = False

    def create_repo(self, repo_id, **kwargs):
        self.created.append(kwargs)
        self.exists = True

    def repo_info(self, repo_id, repo_type):
        from huggingface_hub.utils import RepositoryNotFoundError

        class Missing(RepositoryNotFoundError):
            def __init__(self):
                Exception.__init__(self, "missing")

        self.info_calls += 1
        if not self.exists:
            raise Missing()
        return self.info

    def list_repo_files(self, repo_id, repo_type):
        return []

    def create_commit(self, repo_id, **kwargs):
        self.committed = True


HF = {"kind": "huggingface", "repo_path": "org/comparia", "token": "t"}


def _send(monkeypatch, build_dir, api):
    import huggingface_hub

    from utils.database.models.publish import PublishDestination

    monkeypatch.setattr(huggingface_hub, "HfApi", lambda token: api)
    destination = PublishDestination(
        id=uuid.uuid4(),
        name="hf",
        kind="huggingface",
        config=HF,
        datasets=["raw"],
        enabled=True,
    )
    publish_module.publish([destination], {"raw": build_dir})


@pytest.mark.parametrize("gated", [False, "auto"])
def test_ids_never_go_to_a_repository_anyone_can_read(monkeypatch, tmp_path, gated):
    api = FakeHfApi(gated=gated)
    with pytest.raises(DestinationError, match="readable by anyone"):
        _send(monkeypatch, _raw_build(tmp_path, VOTERS), api)
    assert not api.committed


@pytest.mark.parametrize("private,gated", [(True, False), (False, "manual")])
def test_ids_go_to_a_private_or_reviewed_repository(
    monkeypatch, tmp_path, private, gated
):
    api = FakeHfApi(private=private, gated=gated)
    _send(monkeypatch, _raw_build(tmp_path, VOTERS), api)
    assert api.committed


def test_a_new_repository_for_ids_starts_private(monkeypatch, tmp_path):
    api = FakeHfApi(exists=False)
    _send(monkeypatch, _raw_build(tmp_path, VOTERS), api)
    assert api.created[0]["private"] is True
    assert api.committed


def test_without_ids_the_send_is_as_before(monkeypatch, tmp_path):
    api = FakeHfApi()
    _send(monkeypatch, _raw_build(tmp_path, None), api)
    assert api.committed
    # No visibility check: the push goes as it did before the switch.
    assert api.info_calls == 0


def _load_twice(database, **settings):
    from utils.database.models.app_settings import AppSettings
    from utils.database.session import get_session
    from utils.dataset.voters import load_voter_pseudonyms

    async def scenario():
        if settings:
            async with get_session() as session:
                session.add(AppSettings(id=1, **settings))
                await session.commit()
        first = await load_voter_pseudonyms()
        second = await load_voter_pseudonyms()
        async with get_session() as session:
            row = await session.get(AppSettings, 1)
            stored = row.dataset_voter_key_encrypted if row else None
        return first, second, stored

    return database(scenario)


def test_nothing_without_the_setting(database):
    assert _load_twice(database) == (None, None, None)
    assert _load_twice(database, dataset_voter_ids=False) == (None, None, None)


def test_the_key_is_made_once_kept_and_stored_encrypted(database):
    first, second, stored = _load_twice(database, dataset_voter_ids=True)

    assert first is not None and second is not None
    assert first.key == second.key
    assert first(USER, None) == second(USER, None)
    assert stored is not None
    assert first.key not in stored


def test_the_setting_cannot_be_null():
    assert AppSettingsPatch(dataset_voter_ids=True).dataset_voter_ids is True
    with pytest.raises(ValidationError):
        AppSettingsPatch(dataset_voter_ids=None)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
