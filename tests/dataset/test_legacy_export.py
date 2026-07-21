import asyncio
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.dataset import compute


def test_historical_comparisons_do_not_require_new_consent_records():
    calls = []

    async def comparisons_stream(*args, **kwargs):
        calls.append((args, kwargs))
        yield SimpleNamespace(id="historical-comparison")

    async def comparison_to_turns(_comparison):
        return [{"response_id": "historical-response"}]

    class Exporter:
        total_rows = 0

        def add_rows(self, rows):
            self.total_rows += len(rows)

        def close(self):
            pass

    original_stream = compute.get_db_comparisons_stream
    original_transform = compute.comparison_to_turns
    compute.get_db_comparisons_stream = comparisons_stream
    compute.comparison_to_turns = comparison_to_turns
    try:
        exporter = Exporter()
        asyncio.run(compute.stream_to_exporters({"normal": exporter}))
    finally:
        compute.get_db_comparisons_stream = original_stream
        compute.comparison_to_turns = original_transform

    assert calls == [((), {})]
    assert exporter.total_rows == 1


def test_legacy_raw_cache_receives_terms_marker():
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
                }
            ),
            raw_path,
        )

        compute._write_normal_from_raw_parquet(raw_path, "dataset", output)
        exported = pq.read_table(output / "dataset.parquet")

    assert exported.column("participation_terms_version").to_pylist() == [
        "legacy-pre-versioning"
    ]


if __name__ == "__main__":
    test_historical_comparisons_do_not_require_new_consent_records()
    test_legacy_raw_cache_receives_terms_marker()
