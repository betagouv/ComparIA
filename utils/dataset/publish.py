"""
Send a built dataset to the destinations an instance configured.

The build is the same whatever the destinations are: one directory per
dataset, named after the dataset and not after any repository. Files are given
their published names as they are uploaded, so one build serves several
destinations without being copied.
"""

import logging
import uuid
from pathlib import Path

from sqlmodel import col, select

from utils.database.models.publish import (
    HuggingFaceConfig,
    PublishDestination,
    S3Config,
)
from utils.database.session import get_session
from utils.secrets import SecretUnreadableError

from .models import Datasets

logger = logging.getLogger("comparia.dataset")

# Local build directory and file base name, per dataset.
LOCAL_NAMES: dict[Datasets, str] = {
    "normal": "comparisons",
    "raw": "comparisons-raw",
}

# Files a build produces, as suffixes of the base name.
_SUFFIXES = (".parquet", "_samples.tsv", "_samples.jsonl")

# Published beside the data under their own name: the vocabulary the
# keyword_annotations columns refer to, and the models model_a|b refer to.
# Rewritten every run, so they never need sweeping.
_EXTRA_FILES = ("vote_tags.json", "models.json")

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


async def enabled_destinations(
    destination_id: uuid.UUID | None = None,
) -> list[PublishDestination]:
    async with get_session() as session:
        query = select(PublishDestination).where(
            col(PublishDestination.enabled) == True  # noqa: E712
        )
        if destination_id is not None:
            query = query.where(col(PublishDestination.id) == destination_id)
        rows = await session.exec(query.order_by(col(PublishDestination.created_at)))
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


def _has_voter_ids(build_dir: Path) -> bool:
    """
    Whether the raw parquet holds any voter id, read from the column statistics
    rather than the setting: the file about to leave is what counts. A row
    group without statistics counts as holding some.
    """
    import pyarrow.parquet as pq

    path = build_dir / f"{LOCAL_NAMES['raw']}.parquet"
    if not path.exists():
        return False
    metadata = pq.ParquetFile(path).metadata
    columns = [
        i
        for i in range(metadata.num_columns)
        if metadata.schema.column(i).path == "extra_metadata.voter_id"
    ]
    if not columns:
        return False
    for group in range(metadata.num_row_groups):
        row_group = metadata.row_group(group)
        stats = row_group.column(columns[0]).statistics
        if stats is None or not stats.has_null_count:
            return True
        if stats.null_count < row_group.num_rows:
            return True
    return False


def _require_closed_repo(config: HuggingFaceConfig, dataset: Datasets) -> None:
    """
    Refuse voter ids on a repository anyone can read, before anything is sent.

    A private repository qualifies, and so does a public one gated with manual
    review, which is how the raw datasets have been shared with researchers.
    A gate anyone gets through by clicking does not. A repository that does
    not exist yet is created private, so the push finds it closed.
    """
    from huggingface_hub import HfApi
    from huggingface_hub.utils import RepositoryNotFoundError

    repo_id = _hf_repo(config, dataset)
    api = HfApi(token=config.token)
    try:
        info = api.repo_info(repo_id, repo_type="dataset")
    except RepositoryNotFoundError:
        api.create_repo(repo_id, repo_type="dataset", private=True)
        return
    if info.private or info.gated == "manual":
        return
    raise DestinationError(
        f"'{repo_id}' is readable by anyone, and the raw dataset carries voter "
        "ids: make the repository private or gated with manual review, or turn "
        "the voter ids off"
    )


def publish(
    destinations: list[PublishDestination], built: dict[Datasets, Path]
) -> None:
    """
    Send every built dataset to every destination that asked for it. One
    destination failing does not stop the others, and the run still fails.

    A raw dataset that carries voter ids only goes to a closed Hugging Face
    repository. An S3 bucket is private unless its owner opened it, which the
    run cannot check.
    """
    raw_dir = built.get("raw")
    raw_has_voter_ids = raw_dir is not None and _has_voter_ids(raw_dir)
    failures: list[str] = []

    for destination in destinations:
        try:
            config = destination.parsed_config()
        except SecretUnreadableError as exc:
            logger.error(f"Cannot publish to '{destination.name}': {exc}")
            failures.append(f"{destination.name}: {exc}")
            continue
        for dataset, build_dir in built.items():
            # A destination that asked for a dataset this run did not build
            # simply does not receive it.
            if dataset not in destination.datasets:
                continue
            try:
                if isinstance(config, HuggingFaceConfig):
                    if dataset == "raw" and raw_has_voter_ids:
                        _require_closed_repo(config, dataset)
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
