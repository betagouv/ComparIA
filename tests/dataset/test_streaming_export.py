"""
Equivalence test for the streaming exporter.

Asserts that `StreamingDatasetExporter` (batched parquet row-groups,
memory-bounded) produces the same `.parquet` as the old "accumulate everything
into one DataFrame, then to_parquet" path, for both the `raw` dataset and the
column-dropped/filtered `normal` dataset. Also checks the full `.jsonl` is no
longer emitted (we dropped it) while the small sample previews still are.

Forces several batches so cross-row-group schema coercion is exercised, and
includes null-heavy nested columns (the case most likely to trip up a schema
captured from the first batch).

    uv run --group data python tests/dataset/test_streaming_export.py
"""

import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.dataset.export import StreamingDatasetExporter


def make_rows(n: int) -> list[dict]:
    rows = []
    for i in range(n):
        excluded = i % 3 == 0
        rows.append(
            {
                "response_id": f"r{i}",
                "choice": "a_better" if i % 2 else None,
                "response_a": [
                    {"role": "user", "content": f"q{i}"},
                    {
                        "role": "assistant",
                        "content": f"a{i}",
                        "reasoning_content": None if i % 4 else f"think{i}",
                    },
                ],
                "response_b": [{"role": "user", "content": f"q{i}"}],
                "turn": i % 3,
                "comparison_id": f"c{i}",
                "model_a": "model-a",
                "model_b": "model-b" if i % 5 else "",
                "full_conversation_a": [{"role": "user", "content": f"q{i}"}],
                "full_conversation_b": [{"role": "user", "content": f"q{i}"}],
                "excluded": excluded,
                "metadata": {
                    "tokens_a": i,
                    "tokens_b": None if i % 7 else i + 1,
                    "conso_a": float(i) / 3,
                    "total_conso_a": float(i),
                    "mode": "random",
                    "categories": ["code"] if i % 2 else None,
                },
                "extra_metadata": {
                    "cohorts": None if excluded else "c",
                    "archived": False,
                    "llm_analyzed": True,
                    "archived_reason": None,
                },
            }
        )
    return rows


def old_export(rows, name, export_dir, *, keep, drop_columns):
    """The previous single-shot parquet write, for comparison."""
    df = pd.DataFrame([r for r in rows if keep(r)])
    if drop_columns:
        df = df.drop(columns=list(drop_columns))
    df.to_parquet(export_dir / f"{name}.parquet")
    return df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    # Streaming rows arrive in the same order as the old path (input order),
    # so a plain reset_index comparison is valid.
    return df.reset_index(drop=True)


def check(name, keep, drop_columns, failures):
    rows = make_rows(120)  # > 2 batches at batch_rows=50
    with tempfile.TemporaryDirectory() as d_old, tempfile.TemporaryDirectory() as d_new:
        d_old, d_new = Path(d_old), Path(d_new)

        old_df = old_export(rows, name, d_old, keep=keep, drop_columns=drop_columns)

        exp = StreamingDatasetExporter(
            name, d_new, keep=keep, drop_columns=drop_columns, batch_rows=50
        )
        # Feed in several chunks to mimic the per-comparison streaming.
        for i in range(0, len(rows), 7):
            exp.add_rows(rows[i : i + 7])
        exp.close()

        old_pq = normalize(pd.read_parquet(d_old / f"{name}.parquet"))
        new_pq = normalize(pd.read_parquet(d_new / f"{name}.parquet"))

        # same columns, same order
        if list(old_pq.columns) != list(new_pq.columns):
            failures.append(
                f"{name}: parquet columns differ "
                f"{list(new_pq.columns)} != {list(old_pq.columns)}"
            )
            return
        # same parquet schema (types matter for the published dataset)
        old_schema = pd.read_parquet(d_old / f"{name}.parquet").dtypes.to_dict()
        # compare via pyarrow schema for fidelity
        import pyarrow.parquet as pq

        s_old = pq.read_schema(d_old / f"{name}.parquet")
        s_new = pq.read_schema(d_new / f"{name}.parquet")
        if s_old.remove_metadata() != s_new.remove_metadata():
            failures.append(
                f"{name}: parquet SCHEMA differs:\n OLD {s_old}\n NEW {s_new}"
            )
            return
        # same data
        if not old_pq.equals(new_pq):
            failures.append(f"{name}: parquet DATA differs")
            return

        # the full jsonl must NOT be produced anymore...
        if (d_new / f"{name}.jsonl").exists():
            failures.append(f"{name}: full {name}.jsonl should no longer be written")
            return
        # ...but the small sample previews must still be there.
        for suffix in ("_samples.tsv", "_samples.jsonl"):
            if not (d_new / f"{name}{suffix}").exists():
                failures.append(f"{name}: missing sample file {name}{suffix}")
                return

        print(f"  ok  {name}  ({len(new_pq)} rows, parquet identical, no full jsonl)")


def check_reference_schema(failures):
    """
    The streaming export fixes its parquet schema from `_reference_rows()`. That
    reference MUST yield the exact same schema as real `comparison_to_turns`
    output, otherwise the published schema would silently change. Build a
    fully-populated comparison, compare its inferred schema to the reference's.
    """
    import pyarrow as pa

    import tests.dataset.test_comparison_to_turns as fix
    from utils.dataset import compute

    full = fix.comparison(
        [
            fix.turn(
                fix.user_msg("q"),
                fix.llm_msg("a", 100, reasoning="r"),
                fix.llm_msg("b", 90, reasoning="r"),
                "a_better",
                voted_at=datetime(2024, 1, 1, 12, 0, 5),
            )
        ],
        sys_a="s",
        sys_b="s",
        mode="custom",
        custom_models_selection=["model-a", "model-b"],
        categories=["c"],
        languages=["fr"],
        short_summary="s",
        cohorts="c",
        error={"message": "e", "pos": "a", "is_timeout": False},
        llm_analyzed=True,
        contains_pii=False,
        contains_spam=False,
        archived=False,
        archived_reason="spam",
        archived_at=datetime(2024, 1, 1),
    )
    real = pa.Table.from_pandas(
        pd.DataFrame(fix.comparison_to_turns(full)), preserve_index=False
    ).schema
    ref = pa.Table.from_pandas(
        pd.DataFrame(compute._reference_rows()), preserve_index=False
    ).schema
    if not real.remove_metadata().equals(ref.remove_metadata()):
        failures.append(
            f"_reference_rows schema != real output:\n REAL {real}\n REF {ref}"
        )
    else:
        print("  ok  reference schema matches real comparison_to_turns output")


def check_temporal_nulls(failures):
    """
    Regression: columns that are null for the oldest rows (analysis fields,
    custom_models_selection, …) and populated later must not break the stream.
    With a reference schema the sparse-then-populated sequence must write fine;
    without one it raises ArrowInvalid.
    """
    from utils.dataset import compute

    def row(i, populated):
        return {
            "response_id": f"r{i}",
            "choice": None,
            "response_a": [{"role": "user", "content": "q"}],
            "response_b": [{"role": "user", "content": "q"}],
            "turn": 0,
            "comparison_id": f"c{i}",
            "model_a": "a",
            "model_b": "b",
            "timestamp": datetime(2024, 1, 1),
            "full_conversation_a": [{"role": "user", "content": "q"}],
            "full_conversation_b": [{"role": "user", "content": "q"}],
            "excluded": False,
            "metadata": {
                "tokens_a": 1,
                "tokens_b": None,
                "conso_a": 1.0,
                "conso_b": None,
                "duration_a": 1.0,
                "duration_b": None,
                "latency_a": 1.0,
                "latency_b": None,
                "time_to_vote": 1.0 if populated else None,
                "mode": "random",
                "custom_models_selection": (["m"] if populated else None),
                "categories": (["c"] if populated else None),
                "languages": (["fr"] if populated else None),
                "short_summary": ("s" if populated else None),
                "total_tokens_a": 1,
                "total_tokens_b": None,
                "total_conso_a": 1.0,
                "total_conso_b": None,
            },
            "extra_metadata": {
                "cohorts": "c",
                "error": None,
                "llm_analyzed": (True if populated else None),
                "contains_pii": (False if populated else None),
                "contains_spam": (False if populated else None),
                "archived": False,
                "archived_reason": None,
                "archived_at": None,
            },
        }

    with tempfile.TemporaryDirectory() as d:
        exp = StreamingDatasetExporter(
            "t", Path(d), batch_rows=5, schema_rows=compute._reference_rows()
        )
        try:
            exp.add_rows([row(i, populated=False) for i in range(5)])  # sparse first
            exp.add_rows(
                [row(i, populated=True) for i in range(5, 10)]
            )  # populated later
            exp.close()
        except Exception as e:  # noqa: BLE001
            failures.append(f"temporal-null stream raised {type(e).__name__}: {e}")
            return
        import pyarrow.parquet as pq

        n = pq.ParquetFile(Path(d) / "t.parquet").metadata.num_rows
        if n != 10:
            failures.append(f"temporal-null stream wrote {n} rows, expected 10")
        else:
            print("  ok  temporal-null (sparse-then-populated) streams cleanly")


def run():
    failures = []
    check("comparisons-raw", lambda r: True, (), failures)
    check(
        "comparisons",
        lambda r: not r["excluded"],
        ("excluded", "extra_metadata"),
        failures,
    )
    check_reference_schema(failures)
    check_temporal_nulls(failures)
    print()
    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("Streaming exporter matches the single-shot output.")


def test_streaming_matches_single_shot():
    failures = []
    check("comparisons-raw", lambda r: True, (), failures)
    check(
        "comparisons",
        lambda r: not r["excluded"],
        ("excluded", "extra_metadata"),
        failures,
    )
    assert not failures, failures


def test_reference_schema_matches_real_output():
    failures = []
    check_reference_schema(failures)
    assert not failures, failures


def test_temporal_nulls_stream_cleanly():
    failures = []
    check_temporal_nulls(failures)
    assert not failures, failures


if __name__ == "__main__":
    run()
