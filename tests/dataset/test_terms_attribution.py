import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("LOG_FORMAT", "JSON")

from utils.database.models import LEGACY_PARTICIPATION_TERMS_VERSION  # noqa: E402
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


def test_legacy_comparisons_keep_a_clear_version_marker():
    assert metadata().participation_terms_version == LEGACY_PARTICIPATION_TERMS_VERSION


def test_new_comparisons_export_the_accepted_version():
    assert metadata("2026.07").participation_terms_version == "2026.07"


if __name__ == "__main__":
    test_legacy_comparisons_keep_a_clear_version_marker()
    test_new_comparisons_export_the_accepted_version()
