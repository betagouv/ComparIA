"""Regression tests for the database lint summary."""

import os
import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "RAW")

from utils.database.lint import _label_total_row, _string_reason_column  # noqa: E402


def test_total_label_accepts_an_empty_archived_reason_column():
    total = pl.DataFrame(
        {"archived_reason": [None], "count": [0]},
        schema={"archived_reason": pl.Null, "count": pl.Int64},
    )

    reasons = _string_reason_column(total)
    labelled = _label_total_row(reasons.sum())

    assert labelled[0, "archived_reason"] == "TOTAL"
    assert labelled.schema["archived_reason"] == pl.String
    assert pl.concat([reasons, labelled]).height == 2
