"""Fail-closed policy tests for conversation dataset exports."""

import asyncio
import inspect
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.dataset.compute import (
    _build_exporters,
    _participation_acceptance_filter,
    _reference_rows,
    process_datasets,
)
from utils.dataset.run import main, purge_expired_export_files


def test_default_cli_dataset_does_not_include_raw():
    assert inspect.signature(main).parameters["dataset"].default == "normal"


def test_raw_publication_requires_explicit_opt_in():
    with tempfile.TemporaryDirectory() as directory:

        async def run():
            await process_datasets(["raw"], Path(directory), dry_run=False)

        try:
            asyncio.run(run())
        except ValueError as exc:
            assert "disabled by default" in str(exc)
        else:
            raise AssertionError("Raw publication should fail closed")


def test_unsafe_raw_rows_are_local_only():
    with tempfile.TemporaryDirectory() as directory:

        async def run():
            await process_datasets(
                ["raw"],
                Path(directory),
                dry_run=False,
                allow_raw_publication=True,
                include_unsafe_internal_raw=True,
            )

        try:
            asyncio.run(run())
        except ValueError as exc:
            assert "restricted to an explicit local raw export" in str(exc)
        else:
            raise AssertionError("Unsafe rows must never be published")


def test_filtered_raw_export_rejects_flagged_rows():
    with tempfile.TemporaryDirectory() as directory:
        exporters = _build_exporters(["raw"], "comparia", Path(directory))
        safe_row = _reference_rows()[0]
        unsafe_row = {**safe_row, "response_id": "unsafe", "excluded": True}

        exporters["raw"].add_rows([safe_row, unsafe_row])

        assert exporters["raw"].total_rows == 1


def test_publication_filter_requires_prior_participation_acceptance_for_both_identities():
    sql = str(
        _participation_acceptance_filter().compile(
            compile_kwargs={"literal_binds": True}
        )
    )

    assert "auth_consent_log.user_id = comparison.user_id" in sql
    assert (
        "anonymous_consent_log.anonymous_user_hash = comparison.anonymous_user_hash"
        in sql
    )
    assert sql.count("terms_and_participation") == 2
    assert "research_data_sharing" not in sql
    assert "withdrawn_at" not in sql
    assert sql.count("document_id IS NOT NULL") == 2
    assert sql.count("document_hash IS NOT NULL") == 2
    assert sql.count("consented_at <= comparison.created_at") == 2


def test_cached_raw_data_cannot_be_republished_without_consent_evidence():
    with tempfile.TemporaryDirectory() as directory:

        async def run():
            await process_datasets(
                ["normal"], Path(directory), dry_run=True, use_cache=True
            )

        try:
            asyncio.run(run())
        except ValueError as exc:
            assert "do not carry verifiable participation acceptance" in str(exc)
        else:
            raise AssertionError("Consent-unknown cache must fail closed")


def test_local_export_retention_is_explicit_and_scoped():
    with tempfile.TemporaryDirectory() as directory:
        tmp_path = Path(directory)
        old_export = tmp_path / "comparia" / "comparia.parquet"
        old_export.parent.mkdir()
        old_export.write_text("generated data")
        unrelated = tmp_path / "comparia" / "README.md"
        unrelated.write_text("keep me")
        old_timestamp = time.time() - 3 * 24 * 60 * 60
        os.utime(old_export, (old_timestamp, old_timestamp))
        os.utime(unrelated, (old_timestamp, old_timestamp))

        assert purge_expired_export_files(tmp_path, retention_days=2) == 1
        assert not old_export.exists()
        assert unrelated.exists()


def run_all():
    test_default_cli_dataset_does_not_include_raw()
    test_raw_publication_requires_explicit_opt_in()
    test_unsafe_raw_rows_are_local_only()
    test_filtered_raw_export_rejects_flagged_rows()
    test_publication_filter_requires_prior_participation_acceptance_for_both_identities()
    test_cached_raw_data_cannot_be_republished_without_consent_evidence()
    test_local_export_retention_is_explicit_and_scoped()
    print("Dataset export policy tests passed.")


if __name__ == "__main__":
    run_all()
