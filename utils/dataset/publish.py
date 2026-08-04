"""
Send a built dataset to the destinations an instance configured.

The build is the same whatever the destinations are: one directory per
dataset, named after the dataset and not after any repository. Files are given
their published names as they are uploaded, so one build serves several
destinations without being copied.
"""

import io
import logging
from pathlib import Path

from sqlmodel import col, select

from utils.database.models.publish import (
    HuggingFaceConfig,
    PublishDestination,
    S3Config,
)
from utils.database.session import get_session

from .models import Datasets

logger = logging.getLogger("comparia.dataset")

# Local build directory and file base name, per dataset.
LOCAL_NAMES: dict[Datasets, str] = {
    "normal": "comparisons",
    "raw": "comparisons-raw",
}

# Files a build produces, as suffixes of the base name.
_SUFFIXES = (".parquet", "_samples.tsv", "_samples.jsonl")

# Published beside the data under its own name: the vocabulary the
# keyword_annotations columns refer to. Rewritten every run, so it never needs
# sweeping.
_EXTRA_FILES = ("vote_tags.json",)

# Written and deleted by the check button. Not one of the data suffixes, so a
# run that finds one left behind by an interrupted check leaves it alone.
_PROBE_NAME = ".comparia-write-check"

# The only files a run owns. Anything else on a destination belongs to whoever
# put it there: the dataset card, its images, a LICENSE, the repository's own
# .gitattributes. A run publishes data, it does not tidy other people's files.
_DATA_SUFFIXES = (".parquet", ".jsonl", ".tsv")


class ExportError(Exception):
    """A run that cannot go ahead, or did not finish."""


class DestinationError(ExportError):
    """A destination that is missing, misconfigured, or refused the upload."""


class NotEnoughDiskError(ExportError):
    """Not enough room to build the datasets."""


async def enabled_destinations() -> list[PublishDestination]:
    async with get_session() as session:
        rows = await session.exec(
            select(PublishDestination)
            .where(col(PublishDestination.enabled) == True)  # noqa: E712
            .order_by(col(PublishDestination.created_at))
        )
        return list(rows.all())


def _built_files(
    build_dir: Path, dataset: Datasets, published_base: str
) -> list[tuple[Path, str]]:
    """The files to send, each with the name it is published under."""
    base = LOCAL_NAMES[dataset]
    files = [
        (build_dir / f"{base}{suffix}", f"{published_base}{suffix}")
        for suffix in _SUFFIXES
        if (build_dir / f"{base}{suffix}").exists()
    ]
    if not files:
        raise DestinationError(f"nothing was built for the '{dataset}' dataset")
    files += [
        (build_dir / name, name) for name in _EXTRA_FILES if (build_dir / name).exists()
    ]
    return files


def _hf_repo(config: HuggingFaceConfig, dataset: Datasets) -> str:
    return config.repo_path + ("-raw" if dataset == "raw" else "")


def _push_to_huggingface(
    config: HuggingFaceConfig, dataset: Datasets, build_dir: Path
) -> None:
    from huggingface_hub import CommitOperationAdd, CommitOperationDelete, HfApi

    repo_id = _hf_repo(config, dataset)
    # The published files keep the repository's own name, the way they were
    # named when the repository path came from HF_PUSH_DATASET_PATH.
    published = repo_id.split("/")[-1]

    api = HfApi(token=config.token)
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True)

    operations: list = [
        CommitOperationAdd(path_in_repo=name, path_or_fileobj=str(path))
        for path, name in _built_files(build_dir, dataset, published)
    ]
    written = {op.path_in_repo for op in operations}
    # A data file this run did not write is a leftover from an earlier naming.
    # Left in place it would go on publishing comparisons this run held back,
    # which is the whole point of rebuilding from row zero every time.
    for stale in api.list_repo_files(repo_id, repo_type="dataset"):
        if stale not in written and stale.endswith(_DATA_SUFFIXES):
            operations.append(CommitOperationDelete(path_in_repo=stale))

    api.create_commit(
        repo_id,
        operations=operations,
        repo_type="dataset",
        commit_message=f"Update {dataset} dataset",
    )
    logger.info(f"Pushed the '{dataset}' dataset to '{repo_id}'.")


def _push_to_s3(config: S3Config, dataset: Datasets, build_dir: Path) -> None:
    from minio import Minio

    client = Minio(
        config.endpoint,
        access_key=config.access_key,
        secret_key=config.secret_key,
        secure=config.secure,
        region=config.region,
    )
    base = config.prefix.strip("/")
    folder = f"{base}/{LOCAL_NAMES[dataset]}" if base else LOCAL_NAMES[dataset]

    written = set()
    for path, name in _built_files(build_dir, dataset, LOCAL_NAMES[dataset]):
        key = f"{folder}/{name}"
        client.fput_object(config.bucket, key, str(path))
        written.add(key)

    for obj in client.list_objects(config.bucket, prefix=f"{folder}/", recursive=True):
        name = obj.object_name
        if name and name not in written and name.endswith(_DATA_SUFFIXES):
            client.remove_object(config.bucket, name)

    logger.info(f"Uploaded the '{dataset}' dataset to '{config.bucket}/{folder}'.")


def check_destination(config: HuggingFaceConfig | S3Config) -> None:
    """
    Write a small file and delete it again.

    A read check passes with a read-only token, and the failure then surfaces
    at three in the morning on the first real upload, which is the failure this
    exists to prevent. Raises DestinationError with whatever the destination
    said.
    """
    probe = _PROBE_NAME
    try:
        if isinstance(config, HuggingFaceConfig):
            from huggingface_hub import HfApi

            api = HfApi(token=config.token)
            api.create_repo(config.repo_path, repo_type="dataset", exist_ok=True)
            api.upload_file(
                path_or_fileobj=b"compar:IA sante",
                path_in_repo=probe,
                repo_id=config.repo_path,
                repo_type="dataset",
                commit_message="Check the token can write",
            )
            api.delete_file(probe, repo_id=config.repo_path, repo_type="dataset")
        else:
            from minio import Minio

            client = Minio(
                config.endpoint,
                access_key=config.access_key,
                secret_key=config.secret_key,
                secure=config.secure,
                region=config.region,
            )
            base = config.prefix.strip("/")
            key = f"{base}/{probe}" if base else probe
            client.put_object(config.bucket, key, io.BytesIO(b"compar:IA sante"), 15)
            client.remove_object(config.bucket, key)
    except Exception as exc:
        raise DestinationError(str(exc)) from exc


def publish(
    destinations: list[PublishDestination], built: dict[Datasets, Path]
) -> None:
    """
    Send every built dataset to every destination that asked for it. One
    destination failing does not stop the others, and the run still fails.
    """
    failures: list[str] = []

    for destination in destinations:
        config = destination.parsed_config()
        for dataset, build_dir in built.items():
            # A destination that asked for a dataset this run did not build
            # simply does not receive it.
            if dataset not in destination.datasets:
                continue
            try:
                if isinstance(config, HuggingFaceConfig):
                    _push_to_huggingface(config, dataset, build_dir)
                else:
                    _push_to_s3(config, dataset, build_dir)
            except Exception as exc:
                logger.exception(
                    f"Failed to send the '{dataset}' dataset to '{destination.name}'."
                )
                failures.append(f"{destination.name} ({dataset}): {exc}")

    if failures:
        raise DestinationError("; ".join(failures))
