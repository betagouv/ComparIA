"participation_terms_version": LEGACY_PARTICIPATION_TERMS_VERSION,
                "available_tools": ["x"],                "total_tokens_a": 1,
                "total_tokens_b": 1,
                "total_conso_a": 1.0,
                "total_conso_b": 1.0,
            },
            "extra_metadata": {
                "cohorts": "x",
                "error": {"message": "x", "pos": "a", "is_timeout": False},
                "llm_analyzed": True,
                "contains_pii": False,
                "contains_spam": False,
                "archived": False,
                "archived_reason": "spam",
                "archived_at": datetime(2024, 1, 1),
            },
        }
    ]


def _build_exporters(
    datasets: list[Datasets], export_base_path: Path
) -> dict[Datasets, StreamingDatasetExporter]:
    schema_rows = _reference_rows()
    exporters: dict[Datasets, StreamingDatasetExporter] = {}
    for dataset in datasets:
        name = LOCAL_NAMES[dataset]
        if dataset == "normal":
            exporters[dataset] = StreamingDatasetExporter(
                name,
                export_base_path / name,
                keep=lambda row: not row["excluded"],
                drop_columns=("excluded", "extra_metadata"),
                schema_rows=schema_rows,
            )
        else:
            exporters[dataset] = StreamingDatasetExporter(
                name, export_base_path / name, schema_rows=schema_rows
            )
    return exporters


async def stream_to_exporters(
    exporters: dict[Datasets, StreamingDatasetExporter],
) -> None:
    """
    Single pass over the DB: turn each Comparison into rows and feed every
    exporter (each keeps/drops what it needs). Nothing is accumulated in memory
    beyond the exporters' batch buffers.
    """
    failed_comparison_ids: list[str] = []
    n_comparisons = 0

    async for db_comp in get_db_comparisons_stream():
        try:
            turns = await comparison_to_turns(db_comp)
        except Exception:
            logger.exception(f"Failed to parse Comparison '{db_comp.id}', skipping...")
            failed_comparison_ids.append(str(db_comp.id))
            continue

        for exporter in exporters.values():
            exporter.add_rows(turns)

        n_comparisons += 1
        if n_comparisons % 10_000 == 0:
            written = ", ".join(
                f"{name}={exp.total_rows:,}" for name, exp in exporters.items()
            )
            logger.info(
                f"Progress: {n_comparisons:,} comparisons processed ({written})."
            )

    for exporter in exporters.values():
        exporter.close()

    total_rows = sum(exp.total_rows for exp in exporters.values())
    logger.info(
        f"Finished: {n_comparisons:,} comparisons processed, "
        f"{len(failed_comparison_ids):,} skipped (validation error)."
    )
    if failed_comparison_ids:
        logger.error(
            f"{len(failed_comparison_ids)} comparisons could not be properly parsed: \n"
            + "\n".join(f"- '{id_}'" for id_ in failed_comparison_ids)
        )
    if total_rows == 0:
        raise Exception("No rows produced, aborting export")


def _write_normal_from_raw_parquet(
    raw_parquet_path: Path,
    repo_name: str,
    export_dir: Path,
) -> int:
    """
    Regenerate the normal dataset from the raw parquet without hitting the DB.
    Stays in Arrow throughout (filter + drop + write) to avoid OOM from
    converting large nested columns to Python objects.
    Sample files are written from the first 1000 filtered rows (not random,
    but fast and memory-bounded).
    """
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    DROP_COLS = ["excluded", "extra_metadata"]
    SAMPLE_SIZE = 1000

    export_dir.mkdir(exist_ok=True)
    parquet_path = export_dir / f"{repo_name}.parquet"

    reader = pq.ParquetFile(raw_parquet_path)
    writer: pq.ParquetWriter | None = None
    sample_batches: list[pa.Table] = []
    n_rows = 0

    for batch in reader.iter_batches(batch_size=10_000):
        table = pa.Table.from_batches([batch])
        table = table.filter(pc.equal(table.column("excluded"), False))
        table = table.drop(DROP_COLS)
        metadata_index = table.schema.get_field_index("metadata")
        metadata = table.column(metadata_index)
        if metadata.type.get_field_index("participation_terms_version") == -1:
            fields = [
                *metadata.type,
                pa.field("participation_terms_version", pa.string()),
            ]
            chunks = []
            for chunk in metadata.chunks:
                values = [chunk.field(index) for index in range(chunk.type.num_fields)]
                values.append(
                    pa.array([LEGACY_PARTICIPATION_TERMS_VERSION] * len(chunk))
                )
                chunks.append(
                    pa.StructArray.from_arrays(
                        values,
                        fields=fields,
                        mask=chunk.is_null(),
                    )
                )
            table = table.set_column(
                metadata_index,
                "metadata",
                pa.chunked_array(chunks, type=pa.struct(fields)),
            )

        if len(table) == 0:
            continue

        if writer is None:
            writer = pq.ParquetWriter(parquet_path, table.schema)
        writer.write_table(table)

        if n_rows < SAMPLE_SIZE:
            needed = SAMPLE_SIZE - n_rows
            sample_batches.append(table.slice(0, min(needed, len(table))))

        n_rows += len(table)
        logger.debug(f"Cache: {n_rows:,} rows written to normal parquet")

    if writer:
        writer.close()

    if sample_batches:
        sample_df = pa.concat_tables(sample_batches).to_pandas()
        sample_df.to_csv(export_dir / f"{repo_name}_samples.tsv", sep="\t", index=False)
        sample_df.to_json(
            export_dir / f"{repo_name}_samples.jsonl",
            orient="records",
            lines=True,
            date_format="iso",
        )

    logger.info(
        f"Cache mode: {n_rows:,} rows written ({len(sample_df) if sample_batches else 0:,} sampled)."
    )
    return n_rows


VOTE_TAGS_FILENAME = "vote_tags.json"


async def write_vote_tags_vocabulary(export_dir: Path) -> None:
    """
    Describe the vote tag keys that appear in 'keyword_annotations_a|b'.

    The seven reserved keys mean the same thing on every instance, but an
    instance can add its own, and those are opaque to anyone reading the
    published data. Archived tags stay in the file: rows already published
    still carry them. Reserved tags carry no label here, they are translated
    in the platform rather than stored.
    """
    tags = await get_all_vote_tags()
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / VOTE_TAGS_FILENAME).write_text(
        json.dumps(
            [
                {
                    "key": tag.key,
                    "sign": tag.sign,
                    "reserved": tag.reserved,
                    "archived": tag.archived_at is not None,
                    "labels": tag.labels,
                }
                for tag in tags
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    logger.info(f"Wrote {len(tags)} vote tags to {export_dir / VOTE_TAGS_FILENAME}")


async def process_datasets(
    datasets: list[Datasets],
    export_base_path: Path,
    use_cache: bool = False,
) -> dict[Datasets, Path]:
    """
    Fetch from DB, transform (add metadata, drop what analysis held back) and
    write each dataset to parquet (+ a sample tsv/jsonl preview). Sending the
    result anywhere is the caller's business.

    Args:
        datasets: Names of the datasets to process
        export_base_path: Local directory for export
        use_cache: If True and raw parquet exists, regenerate normal from it (skips DB)

    Returns the directory each dataset was written to.
    """
    logger.info(f"Starting processing datasets…")

    raw_name = LOCAL_NAMES["raw"]
    raw_parquet_path = export_base_path / raw_name / f"{raw_name}.parquet"

    logger.info(f"Folder defined for dataset: {export_base_path}")

    if use_cache and "normal" in datasets and raw_parquet_path.exists():
        logger.info(f"Cache mode: reading from {raw_parquet_path}")
        normal_name = LOCAL_NAMES["normal"]
        normal_export_dir = export_base_path / normal_name
        _write_normal_from_raw_parquet(raw_parquet_path, normal_name, normal_export_dir)
        await write_vote_tags_vocabulary(normal_export_dir)
        return {"normal": normal_export_dir}

    if use_cache:
        logger.warning(
            f"Cache requested but raw parquet not found at {raw_parquet_path}, running full export"
        )
    logger.info(f"Streaming datasets to local files: {', '.join(datasets)}…")
    exporters = _build_exporters(datasets, export_base_path)
    await stream_to_exporters(exporters)

    built = {dataset: export_base_path / LOCAL_NAMES[dataset] for dataset in exporters}
    for export_dir in built.values():
        await write_vote_tags_vocabulary(export_dir)
    return built
