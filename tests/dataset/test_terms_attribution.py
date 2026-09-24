"""
Unit tests for the accepted terms version in the dataset export.

Run with pytest, or directly:
    uv run python tests/dataset/test_terms_attribution.py
"""

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("LOG_FORMAT", "JSON")

from utils.database.models import LEGACY_PARTICIPATION_TERMS_VERSION  # noqa: E402
from utils.dataset import compute  # noqa: E402
from utils.dataset.models import DatasetComparisonBaseMetadata  # noqa: E402


def metadata(version=None):
    values = {
        "mode": "random",
        "custom_models_selection": None,
        "categories": None,
        "languages": None,
        "short_summary": None,
    }
    if version is not None:
        values["participation_terms_version"] = version
    return DatasetComparisonBaseMetadata.model_validate(SimpleNamespace(**values))


def test_comparisons_without_a_version_keep_the_legacy_marker():
    assert metadata().participation_terms_version == LEGACY_PARTICIPATION_TERMS_VERSION


def test_new_comparisons_export_the_accepted_version():
    assert metadata("2026.07").participation_terms_version == "2026.07"


def test_rows_from_an_old_raw_cache_receive_the_legacy_marker():
    import pyarrow as pa
    import pyarrow.parquet as pq

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        raw_path = root / "raw.parquet"
        output = root / "output"
        pq.write_table(
            pa.table(
                {
                    "response_id": ["historical-response"],
                    "excluded": [False],
                    "extra_metadata": [{"archived": False}],
                    "metadata": [{"mode": "random"}],
                }
            ),
            raw_path,
        )

        compute._write_normal_from_raw_parquet(raw_path, "dataset", output)
        exported = pq.read_table(output / "dataset.parquet")

    assert "participation_terms_version" not in exported.column_names
    assert exported.column("metadata").to_pylist() == [
        {
            "mode": "random",
            "participation_terms_version": LEGACY_PARTICIPATION_TERMS_VERSION,
        }
    ]


if __name__ == "__main__":
    test_comparisons_without_a_version_keep_the_legacy_marker()
    test_new_comparisons_export_the_accepted_version()
    test_rows_from_an_old_raw_cache_receive_the_legacy_marker()
