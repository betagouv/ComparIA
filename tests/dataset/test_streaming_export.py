pd.DataFrame(fix.comparison_to_turns(full)), preserve_index=False    ).schema
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
