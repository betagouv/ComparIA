"""
Export ComparIA datasets from PostgreSQL to HuggingFace Hub.

This script:
1. Fetches Comparisons from the database
2. Validate data with Dataset* models
3. Filters out archived, errored, not analyzed and specific cohorts (Pix, do-not-track) for the public dataset
4. Exports to parquet (+ a small sample tsv/jsonl preview)
5. Uploads to HuggingFace Hub repositories

Usage:
    see `./comparia-cli generate datasets --help`

Required env vars: COMPARIA_DB_URI, HF_PUSH_DATASET_KEY (if not --dry-run)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID

from async_lru import alru_cache
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import and_, col, select

from backend.arena.web_search import merge_web_search_with_content
from backend.config import settings
from backend.llms.models import APILLMDataBase
from backend.settings.legal import DEFAULT_LEGAL_LANGUAGE, get_active_legal_document
from backend.vote_tags.services import get_all_vote_tags
from utils.database.models import (
    LEGACY_PARTICIPATION_TERMS_VERSION,
    Comparison,
    SurveyAnswer,
    SurveyQuestion,
)
from utils.database.models.llms import LLMData
from utils.database.models.messages import LLMMessage
from utils.database.session import get_session
from utils.database.utils import get_db_comparisons_counts, get_db_comparisons_stream

from .export import StreamingDatasetExporter, commit_and_push
from .models import (
    DatasetComparisonBaseMetadata,
    DatasetComparisonExtraMetadata,
    Datasets,
    RespondentAnswers,
)

logger = logging.getLogger("comparia.dataset")


@alru_cache
async def get_llms_data() -> dict[UUID, APILLMDataBase]:
    """
    Query LLM data from db.
    Used to enrich datasets with metadata (params count, energy consumption).
    """

    try:
        async with get_session() as session:
            llms = (
                await session.exec(
                    select(LLMData).where(LLMData.status.in_(["enabled", "archived"]))
                )
            ).all()
        return {llm.id: APILLMDataBase.model_validate(llm) for llm in llms}
    except Exception as e:
        logger.error(f"Error loading LLMs data: {e}")
        raise


def _respondent_key(
    user_id: UUID | None, anonymous_user_hash: str | None
) -> str | None:
    """
    Mirrors how 'comparison' itself records a respondent: exactly one of
    user_id/anonymous_user_hash is set (never both, never neither once a
    comparison has a visitor attached). None means neither is set, which the
    caller treats as "no survey answers to attach".
    """
    if user_id is not None:
        return f"user:{user_id}"
    if anonymous_user_hash:
        return f"anon:{anonymous_user_hash}"
    return None


def publishable_survey_terms_versions(active_version: str | None) -> set[str]:
    """
    The SurveyAnswer.terms_version values whose answers may be published in
    the public dataset. This is THE place to edit when the terms are bumped:
    add a version here only if its consent text covers research publication
    of survey answers to the same extent as the current one.

    - active published "terms" document version: IN. It is what
      backend.auth.services.get_current_terms_acceptance_version() stamps on
      every answer (see backend/survey/router.py), so it is the only version
      whose text we know the respondent actually accepted.
    - LEGACY_PARTICIPATION_TERMS_VERSION ("legacy-pre-versioning"): OUT.
      get_current_terms_acceptance_version() returns that marker when NO terms
      document is published at all, i.e. the respondent accepted nothing —
      and backend/auth/services.py:erase_user_account explicitly notes survey
      answers were never offered for publication under the research terms.
    - NULL: OUT. Old rows predate version recording, so no proof of consent
      exists; when unsure, do not publish.
    - Any other (retired or unknown) version: OUT, for the same reason.

    If nothing is currently published, nothing is publishable.
    """
    return {active_version} if active_version else set()


def _survey_answers_query(publishable_versions: set[str]):
    """
    Published, non-archived questions joined to answers whose consent version
    is publishable (see `publishable_survey_terms_versions`). The consent gate
    lives here, in the WHERE clause: NULL (not matched by IN) and
    legacy/retired versions never leave the database.
    """
    return (
        select(
            SurveyQuestion.key,
            SurveyQuestion.input_type,
            SurveyAnswer.user_id,
            SurveyAnswer.anonymous_user_hash,
            SurveyAnswer.option_key,
        )
        .join(
            SurveyAnswer,
            col(SurveyAnswer.question_id) == col(SurveyQuestion.id),
        )
        .where(
            col(SurveyQuestion.published) == True,
            col(SurveyQuestion.archived_at).is_(None),
            col(SurveyAnswer.terms_version).in_(publishable_versions),
        )
        .order_by(col(SurveyAnswer.answered_at))
    )


@alru_cache
async def get_survey_respondent_answers() -> dict[str, RespondentAnswers]:
    """
    Every current answer to a published, non-archived survey question,
    grouped by respondent (see `_respondent_key`). Loaded once (cached) for
    the whole export rather than queried per turn or per comparison: the
    export streams millions of turns, but the answer table itself is small
    (one row per option per question per respondent), so one join beats a
    query per row.

    Unpublished and archived questions are filtered out here, at the source:
    their answers never enter the returned mapping and so never reach the
    dataset, regardless of what a Comparison's row later looks up.

    Answers are also filtered on consent: only those recorded under a terms
    version listed in `publishable_survey_terms_versions` (see that function
    for which versions qualify and why) enter the dataset.

    Answers are stored replace-in-place (see
    utils/database/models/survey.py), so whatever is in the table now IS the
    respondent's current answer; there is no history to reconcile. Rows are
    folded in 'answered_at' order so that if a single-choice question is ever
    somehow represented by more than one row for the same respondent, the
    most recently answered one wins deterministically.
    """
    async with get_session() as session:
        active_terms = await get_active_legal_document("terms", DEFAULT_LEGAL_LANGUAGE)
        publishable_versions = publishable_survey_terms_versions(
            active_terms.version if active_terms else None
        )
        rows = (await session.exec(_survey_answers_query(publishable_versions))).all()

    answers: dict[str, RespondentAnswers] = {}
    for question_key, input_type, user_id, anonymous_user_hash, option_key in rows:
        respondent = _respondent_key(user_id, anonymous_user_hash)
        if respondent is None:
            continue
        per_respondent = answers.setdefault(respondent, {})
        if input_type == "checkbox_group":
            per_respondent.setdefault(question_key, [])  # type: ignore[assignment]
            per_respondent[question_key].append(option_key)  # type: ignore[union-attr]
        else:
            per_respondent[question_key] = option_key
    return answers


async def count_dataset_rows(datasets: list[Datasets]):
    """Display row counts for each dataset without performing export."""
    try:
        logger.info("Counting rows for each dataset...")
        counts = await get_db_comparisons_counts(
            {
                "normal": and_(
                    col(Comparison.archived) == False,
                    col(Comparison.llm_analyzed) == True,
                    col(Comparison.contains_pii) != True,
                    col(Comparison.contains_spam) != True,
                    col(Comparison.error) == JSONB.NULL,
                    col(Comparison.cohorts).in_((None, "")),
                ),
                "raw": col(Comparison.id) != None,
            }
        )

        for dataset, count in counts.items():
            logger.info(f"{dataset:15} {count:>10,} rows")
    except Exception as e:
        logger.error(f"An error occurred while counting rows.")
        raise


def _conso(llm: LLMData | None, msg: LLMMessage | None) -> float | None:
    # None for legacy comparisons with empty/unknown llm_id, or no answer.
    if llm is None or msg is None:
        return None
    return (llm.wh_per_million_token / 1_000_000) * msg.tokens / 1_000


def _latency(msg: LLMMessage | None) -> float | None:
    return (msg.responded_at - msg.created_at).total_seconds() if msg else None


def _duration(msg: LLMMessage | None) -> float | None:
    return (msg.updated_at - msg.responded_at).total_seconds() if msg else None


def _time_to_vote(
    voted_at: datetime | None, msg_a: LLMMessage | None, msg_b: LLMMessage | None
) -> float | None:
    # Seconds between both models finishing (the later of the two) and the vote.
    # Requires both answers: a one-sided turn has no "both finished" moment, so
    # we return None rather than a misleading value (legacy/corrupt rows can have
    # voted_at set with a side missing, even though the live route forbids it).
    if voted_at is None or msg_a is None or msg_b is None:
        return None
    return (voted_at - max(msg_a.updated_at, msg_b.updated_at)).total_seconds()


def _total(turns_metadata: list[dict], key: str) -> float | int | None:
    # Sum across turns, but only when every turn has the value.
    values = [meta[key] for meta in turns_metadata]
    return sum(values) if all(v is not None for v in values) else None


def _llm_response_entry(msg: LLMMessage) -> dict:
    # Raw values on purpose: the ORM LLMMessage is already an LLMMessageFinal
    # instance, so the old pipeline's nested validation never re-ran (Pydantic
    # revalidate_instances="never"): no stripping, no constraint checks. The
    # only comparisons it dropped were those that hit a TypeError in the
    # tokens/latency/duration math below, which we reproduce by construction.
    return {
        "content": msg.content,
        "reasoning_content": msg.reasoning_content,
        "role": msg.role,
    }


async def comparison_to_turns(db_comparison: Comparison) -> list[dict]:
    """
    Flatten a Comparison into one row per turn.

    Reads ORM attributes directly instead of routing the whole nested object
    graph (turns, user/assistant/system messages, full conversations) through
    Pydantic validate+dump, which was the dominant cost on large exports. The
    flat metadata blocks still go through their Pydantic models so their
    serialization stays byte-for-byte identical. The equivalence with the old
    pipeline is pinned by tests/dataset/test_comparison_to_turns.py.
    """
    comp = db_comparison
    llms = await get_llms_data()
    llm_a = llms.get(comp.llm_id_a)  # .get() tolerates empty/unknown llm_id
    llm_b = llms.get(comp.llm_id_b)

    # Published-questions-only socio-demographic answers for whoever had this
    # conversation. Same dict for every turn of this comparison: the
    # respondent doesn't change turn to turn, so this is computed once here
    # rather than once per turn. JSON-encoded (see `_reference_rows`) because
    # the key set is admin-editable and can't be pinned as a fixed struct.
    respondent_answers = await get_survey_respondent_answers()
    respondent_id = _respondent_key(comp.user_id, comp.anonymous_user_hash)
    respondent = respondent_answers.get(respondent_id, {}) if respondent_id else {}
    respondent_json = json.dumps(respondent, ensure_ascii=False, sort_keys=True)

    # A side's full conversation opens with its system prompt (when present),
    # then alternates user / assistant for every turn.
    full_conversation_a: list[dict] = (
        [{"role": "system", "content": comp.system_msg_a}] if comp.system_msg_a else []
    )
    full_conversation_b: list[dict] = (
        [{"role": "system", "content": comp.system_msg_b}] if comp.system_msg_b else []
    )

    partial_rows: list[dict] = []
    turns_metadata: list[dict] = []

    for turn in comp.turns:
        if turn.user_msg is None or turn.user_msg.content is None:
            raise ValueError("Turn has no user message")

        msg_a, msg_b = turn.llm_msg_a, turn.llm_msg_b

        raw_content = turn.user_msg.content
        content = (
            merge_web_search_with_content(raw_content, turn.user_msg.web_search_results)
            if turn.user_msg.web_search_results
            else raw_content
        )
        user_entry = {
            "role": turn.user_msg.role,
            "content": content,
            "user_content": raw_content,
        }
        response_a = [user_entry] + ([_llm_response_entry(msg_a)] if msg_a else [])
        response_b = [user_entry] + ([_llm_response_entry(msg_b)] if msg_b else [])
        full_conversation_a.extend(response_a)
        full_conversation_b.extend(response_b)

        # Keys are emitted in DatasetTurnMetadata field order so the output
        # matches the old model_dump (the equivalence test pins this).
        turns_metadata.append(
            {
                "tokens_a": msg_a.tokens if msg_a else None,
                "tokens_b": msg_b.tokens if msg_b else None,
                "conso_a": _conso(llm_a, msg_a),
                "conso_b": _conso(llm_b, msg_b),
                "duration_a": _duration(msg_a),
                "duration_b": _duration(msg_b),
                "latency_a": _latency(msg_a),
                "latency_b": _latency(msg_b),
                "time_to_vote": _time_to_vote(turn.voted_at, msg_a, msg_b),
            }
        )
        partial_rows.append(
            {
                "response_id": str(turn.id),
                "choice": turn.choice,
                "response_a": response_a,
                "response_b": response_b,
            }
        )

    if not partial_rows:
        return []

    # base_meta and extra_meta still go through their models: they read raw ORM
    # columns that need coercion (e.g. custom_models_selection tuple, error ->
    # ErrorDetails). The totals are appended in DatasetComparisonMetadata field
    # order so the merged dict matches the old model_dump output exactly.
    base_meta = DatasetComparisonBaseMetadata.model_validate(comp).model_dump()
    comp_meta = {
        **base_meta,
        "total_tokens_a": _total(turns_metadata, "tokens_a"),
        "total_tokens_b": _total(turns_metadata, "tokens_b"),
        "total_conso_a": _total(turns_metadata, "conso_a"),
        "total_conso_b": _total(turns_metadata, "conso_b"),
    }
    extra_meta = DatasetComparisonExtraMetadata.model_validate(comp).model_dump()

    excluded = bool(
        extra_meta["cohorts"]
        or extra_meta["archived"] is not False
        or extra_meta["contains_pii"]
        or extra_meta["contains_spam"]
        or extra_meta["error"] is not None
        or extra_meta["llm_analyzed"] is not True
    )
    comparison_id = str(comp.id)

    return [
        {
            **row,
            "turn": idx,
            "comparison_id": comparison_id,
            "model_a": str(comp.llm_id_a),
            "model_b": str(comp.llm_id_b),
            "timestamp": comp.created_at,
            "full_conversation_a": full_conversation_a,
            "full_conversation_b": full_conversation_b,
            "excluded": excluded,
            "metadata": {**turn_meta, **comp_meta},
            "extra_metadata": extra_meta,
            "respondent": respondent_json,
        }
        for idx, (row, turn_meta) in enumerate(zip(partial_rows, turns_metadata))
    ]


def _reference_rows() -> list[dict]:
    """
    One fully-populated row, mirroring `comparison_to_turns` output exactly, used
    to fix the parquet schema before streaming (see StreamingDatasetExporter).
    Every nullable field carries a value here so the column types are known up
    front instead of inferred from a first batch where they may be all-null.
    The equivalence test pins that this matches real `comparison_to_turns` output.
    """
    user = {"role": "user", "content": "x", "user_content": "x"}
    assistant = {"content": "x", "reasoning_content": "x", "role": "assistant"}
    system = {"role": "system", "content": "x"}
    return [
        {
            "response_id": "ref",
            "choice": "a_better",
            "response_a": [user, assistant],
            "response_b": [user, assistant],
            "turn": 0,
            "comparison_id": "ref",
            "model_a": "x",
            "model_b": "x",
            "timestamp": datetime(2024, 1, 1),
            "full_conversation_a": [system, user, assistant],
            "full_conversation_b": [system, user, assistant],
            "excluded": False,
            "metadata": {
                "tokens_a": 1,
                "tokens_b": 1,
                "conso_a": 1.0,
                "conso_b": 1.0,
                "duration_a": 1.0,
                "duration_b": 1.0,
                "latency_a": 1.0,
                "latency_b": 1.0,
                "time_to_vote": 1.0,
                "mode": "random",
                "custom_models_selection": ["x"],
                "categories": ["x"],
                "languages": ["x"],
                "short_summary": "x",
                "participation_terms_version": LEGACY_PARTICIPATION_TERMS_VERSION,
                "total_tokens_a": 1,
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
            # JSON-encoded string, not a struct: the question key set is
            # admin-editable (new questions can be published at any time), so
            # a struct/map column would either change shape release to
            # release or force every answer to the same value type. A string
            # column is the one shape that stays fixed regardless of what
            # questions exist. See `get_survey_respondent_answers`.
            "respondent": json.dumps({"x": "x", "y": ["x", "y"]}, sort_keys=True),
        }
    ]


def _build_exporters(
    datasets: list[Datasets], repo_prefix: str, export_base_path: Path
) -> dict[Datasets, StreamingDatasetExporter]:
    schema_rows = _reference_rows()
    exporters: dict[Datasets, StreamingDatasetExporter] = {}
    for dataset in datasets:
        repo_name = repo_prefix + ("-raw" if dataset == "raw" else "")
        if dataset == "normal":
            exporters[dataset] = StreamingDatasetExporter(
                repo_name,
                export_base_path / repo_name,
                keep=lambda row: not row["excluded"],
                drop_columns=("excluded", "extra_metadata"),
                schema_rows=schema_rows,
            )
        else:
            exporters[dataset] = StreamingDatasetExporter(
                repo_name, export_base_path / repo_name, schema_rows=schema_rows
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


def get_repo_infos() -> tuple[str, str]:
    if not settings.HF_PUSH_DATASET_PATH:
        raise Exception("Missing env var 'HF_PUSH_DATASET_PATH'")

    try:
        org, prefix = settings.HF_PUSH_DATASET_PATH.split("/", 1)
        assert org
        assert prefix
        return org, prefix
    except Exception as exc:
        raise Exception(
            "'HF_PUSH_DATASET_PATH' should match the pattern '{organisation}/{repo_prefix}'"
        )


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
        # Same idea as 'participation_terms_version' above: a raw parquet
        # cached from before 'respondent' existed has no such column at all.
        # Backfill '{}' (answered nothing) rather than producing a normal
        # dataset with a column missing entirely.
        if table.schema.get_field_index("respondent") == -1:
            table = table.append_column(
                "respondent", pa.array(["{}"] * len(table), type=pa.string())
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


README_FILENAME = "README.md"


def write_dataset_readme(export_dir: Path, repo_name: str) -> None:
    """
    Minimal dataset card. There was no card generated by this pipeline before
    (the HF repo only ever received the parquet, samples and vote tags
    vocabulary via `commit_and_push`'s `upload_folder`), so this is the
    smallest one that documents what a researcher cannot infer by looking at
    the columns: what 'respondent' means and why two releases can disagree
    about the same row. Rewritten in full on every export, same as
    'vote_tags.json' above, rather than hand-edited.
    """
    export_dir.mkdir(parents=True, exist_ok=True)
    (export_dir / README_FILENAME).write_text(
        f"""# {repo_name}

One row per conversation turn, exported from ComparIA.

## The `respondent` field

Each row carries a `respondent` field: a JSON-encoded object mapping every
*published* survey question's key to the answer given by whoever had that
conversation, for example `{{"age": "25_34", "job": ["dev", "student"]}}`.

- A `select` question maps its key to a single option key (a string).
- A `checkbox_group` question maps its key to a list of option keys.
- `{{}}` means the respondent was not asked, or answered nothing.
- Only questions marked "published" in the survey admin are included here;
  unpublished or archived questions, and their answers, never leave the
  instance.
- Keys are the question's and options' stable, immutable identifiers, not
  their (editable, per-locale) display labels.

**Caveat:** demographic answers reflect each respondent's most recent
answer, not the answer they held when the conversation happened. A
respondent who updates an answer changes it for all their past rows, so two
releases can disagree about the same `response_id`.
""",
        encoding="utf-8",
    )
    logger.info(f"Wrote dataset card to {export_dir / README_FILENAME}")


async def process_datasets(
    datasets: list[Datasets],
    export_base_path: Path,
    dry_run: bool = False,
    use_cache: bool = False,
):
    """
    Process a single dataset: fetch from DB, transform (anonymize, add metadata),
    Export to parquet (+ sample tsv/jsonl preview), and push to HF Hub.

    Args:
        dataset_names: Names of the datasets to process
        export_base_path: Local directory for export
        dry_run: If True, skip HuggingFace upload
        use_cache: If True and raw parquet exists, regenerate normal from it (skips DB)
    """
    logger.info(f"Starting processing datasets…")

    repo_org, repo_prefix = get_repo_infos()
    raw_parquet_path = (
        export_base_path / (repo_prefix + "-raw") / (repo_prefix + "-raw.parquet")
    )

    logger.info(f"Folder defined for dataset: {export_base_path}")

    if use_cache and "normal" in datasets and raw_parquet_path.exists():
        logger.info(f"Cache mode: reading from {raw_parquet_path}")
        normal_repo_name = repo_prefix
        normal_export_dir = export_base_path / normal_repo_name
        _write_normal_from_raw_parquet(
            raw_parquet_path, normal_repo_name, normal_export_dir
        )
        await write_vote_tags_vocabulary(normal_export_dir)
        write_dataset_readme(normal_export_dir, normal_repo_name)
        if dry_run:
            logger.info(
                f"[DRY RUN] Skipping HuggingFace upload for '{normal_repo_name}'"
            )
        else:
            commit_and_push(repo_org, normal_repo_name, normal_export_dir)
    else:
        if use_cache:
            logger.warning(
                f"Cache requested but raw parquet not found at {raw_parquet_path}, running full export"
            )
        logger.info(f"Streaming datasets to local files: {', '.join(datasets)}…")
        exporters = _build_exporters(datasets, repo_prefix, export_base_path)
        await stream_to_exporters(exporters)

        for dataset, exporter in exporters.items():
            repo_name = exporter.dataset_name
            repo_path = export_base_path / repo_name
            await write_vote_tags_vocabulary(repo_path)
            write_dataset_readme(repo_path, repo_name)
            if dry_run:
                logger.info(f"[DRY RUN] Skipping HuggingFace upload for '{repo_name}'")
            else:
                commit_and_push(repo_org, repo_name, repo_path)
