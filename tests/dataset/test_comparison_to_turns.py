"""
Equivalence test pinning the fast `comparison_to_turns` against the original
Pydantic pipeline (kept verbatim below as the oracle).

The export builder was rewritten to read ORM attributes directly instead of
re-validating and re-dumping the whole nested object graph. This test builds
synthetic Comparison fixtures covering the tricky cases (legacy empty llm_id,
a side that didn't answer, whitespace/empty content, missing system prompts,
the metadata/excluded permutations, and the comparisons the old pipeline
silently skipped) and asserts the new output is identical row-for-row,
key-order included.

No DB and no pytest required:
    uv run --group data python tests/dataset/test_comparison_to_turns.py
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.database.models import Comparison, Turn
from utils.database.models.messages import LLMMessage, UserMessage
from utils.dataset import compute
from utils.dataset.models import (
    DatasetComparison,
    DatasetComparisonBaseMetadata,
    DatasetComparisonExtraMetadata,
)

# --- llms fixture (only `.wh_per_million_token` is read) -------------------

LLMS = {
    "model-a": SimpleNamespace(wh_per_million_token=1000.0),
    "model-b": SimpleNamespace(wh_per_million_token=500.0),
}


async def _llms_data():
    return LLMS


compute.get_llms_data = _llms_data  # patch, so no DB is needed


def comparison_to_turns(db_comparison: Comparison) -> list[dict]:
    """Sync wrapper, `compute.comparison_to_turns` is a coroutine."""
    return asyncio.run(compute.comparison_to_turns(db_comparison))


# --- oracle: the original implementation, unchanged ------------------------


def oracle_comparison_to_turns(db_comparison: Comparison) -> list[dict]:
    ctx = {
        "llm_a": LLMS.get(db_comparison.llm_id_a),
        "llm_b": LLMS.get(db_comparison.llm_id_b),
        "metadata": DatasetComparisonBaseMetadata.model_validate(
            db_comparison
        ).model_dump(),
        "extra_metadata": DatasetComparisonExtraMetadata.model_validate(
            db_comparison
        ).model_dump(),
    }
    comparison = DatasetComparison.model_validate(db_comparison, context=ctx)
    comp_data = comparison.model_dump()
    comp_meta = comp_data.pop("metadata_")
    comp_extra_meta = comp_data.pop("extra_metadata_")
    comp_turns = comp_data.pop("turns_")

    turns = []
    for idx, turn_data in enumerate(comp_turns):
        turn_meta = turn_data.pop("metadata_")
        turns.append(
            {
                **turn_data,
                "turn": idx,
                **comp_data,
                "metadata": {**turn_meta, **comp_meta},
                "extra_metadata": comp_extra_meta,
            }
        )
    return turns


# --- fixture builders ------------------------------------------------------

T0 = datetime(2024, 1, 1, 12, 0, 0)


def user_msg(content="hi", **kw):
    return UserMessage(content=content, created_at=T0, **kw)


def llm_msg(
    content="answer",
    tokens=120,
    reasoning=None,
    generation_id="gen-1",
    created_at=T0,
    responded_at=datetime(2024, 1, 1, 12, 0, 1),
    updated_at=datetime(2024, 1, 1, 12, 0, 3),
    **kw,
):
    return LLMMessage(
        content=content,
        reasoning_content=reasoning,
        tokens=tokens,
        generation_id=generation_id,
        is_cached=False,
        created_at=created_at,
        responded_at=responded_at,
        updated_at=updated_at,
        **kw,
    )


def turn(user, a, b, choice=None, voted_at=None):
    t = Turn(created_at=T0)
    t.user_msg = user
    t.llm_msg_a = a
    t.llm_msg_b = b
    t.choice = choice
    t.voted_at = voted_at
    return t


def comparison(
    turns,
    *,
    sys_a=None,
    sys_b=None,
    llm_id_a="model-a",
    llm_id_b="model-b",
    mode="random",
    custom_models_selection=None,
    categories=None,
    languages=None,
    short_summary=None,
    cohorts=None,
    error=None,
    llm_analyzed=None,
    contains_pii=None,
    contains_spam=None,
    archived=None,
    archived_reason=None,
    archived_at=None,
):
    c = Comparison(ip="0.0.0.0", mode=mode, llm_id_a=llm_id_a, llm_id_b=llm_id_b)
    c.custom_models_selection = custom_models_selection
    c.categories = categories
    c.languages = languages
    c.short_summary = short_summary
    c.cohorts = cohorts
    c.error = error
    c.llm_analyzed = llm_analyzed
    c.contains_pii = contains_pii
    c.contains_spam = contains_spam
    c.archived = archived
    c.archived_reason = archived_reason
    c.archived_at = archived_at
    c.system_msg_a = sys_a
    c.system_msg_b = sys_b
    c.turns = turns
    return c


# --- cases that must produce identical output ------------------------------


def equivalent_cases():
    yield "happy 2-turn, both answer, systems, analyzed/kept", comparison(
        [
            turn(user_msg("q1"), llm_msg("a1", 100), llm_msg("b1", 200), "a_better"),
            turn(
                user_msg("q2"),
                llm_msg("a2", 50, reasoning="because"),
                llm_msg("b2", 80),
            ),
        ],
        sys_a="sys a",
        sys_b="sys b",
        cohorts="some-cohort",
        llm_analyzed=True,
        archived=False,
    )

    yield "legacy empty llm_id_a -> llm None -> conso None", comparison(
        [turn(user_msg(), llm_msg("a", 100), llm_msg("b", 100))],
        llm_id_a="",
    )

    yield "side b did not answer (llm_msg_b None)", comparison(
        [turn(user_msg(), llm_msg("a", 70), None, "a_better")],
        cohorts="c",
        llm_analyzed=True,
        archived=False,
    )

    yield "no system messages", comparison(
        [turn(user_msg(), llm_msg("a", 10), llm_msg("b", 20))],
    )

    # The old pipeline left LLM content/reasoning RAW (the ORM object is already
    # an LLMMessageFinal instance, so revalidate_instances="never" skipped the
    # StripAndEmptyAsNone validators). We must preserve that, not strip.
    yield "llm content/reasoning passed through raw (no strip)", comparison(
        [
            turn(
                user_msg("  spaced  "),
                llm_msg("  trimmed me  ", 10, reasoning="   "),
                llm_msg("ok", 10, reasoning="  real  "),
            )
        ],
    )

    # generation_id is never read downstream, so a None one is not a skip.
    yield "llm generation_id None is not a skip", comparison(
        [turn(user_msg(), llm_msg("a", 10, generation_id=None), llm_msg("b", 10))],
    )

    # tokens None only blows up conso when the llm IS known; with a legacy empty
    # llm_id the conso is None and the row is produced with tokens_a=None.
    yield "legacy llm + tokens None -> kept, conso None", comparison(
        [turn(user_msg(), llm_msg("a", tokens=None), None)],
        llm_id_a="",
    )

    yield "error present -> normalized + excluded", comparison(
        [turn(user_msg(), llm_msg("a", 10), llm_msg("b", 10))],
        error={"message": "boom"},
        cohorts="c",
        llm_analyzed=True,
        archived=False,
    )

    yield "custom_models_selection list serialization", comparison(
        [turn(user_msg(), llm_msg("a", 10), llm_msg("b", 10))],
        mode="custom",
        custom_models_selection=["model-a", "model-b"],
        categories=["code"],
        languages=["fr", "en"],
        short_summary="a summary",
    )

    # excluded permutations
    yield "kept: cohort set, analyzed, archived False", comparison(
        [turn(user_msg(), llm_msg("a", 10), llm_msg("b", 10))],
        cohorts="c",
        llm_analyzed=True,
        archived=False,
    )
    yield "excluded: no cohort", comparison(
        [turn(user_msg(), llm_msg("a", 10), llm_msg("b", 10))],
        cohorts=None,
        llm_analyzed=True,
        archived=False,
    )
    yield "excluded: archived True", comparison(
        [turn(user_msg(), llm_msg("a", 10), llm_msg("b", 10))],
        cohorts="c",
        llm_analyzed=True,
        archived=True,
        archived_reason="spam",
    )
    yield "excluded: not analyzed", comparison(
        [turn(user_msg(), llm_msg("a", 10), llm_msg("b", 10))],
        cohorts="c",
        llm_analyzed=False,
        archived=False,
    )
    yield "excluded: contains_pii True", comparison(
        [turn(user_msg(), llm_msg("a", 10), llm_msg("b", 10))],
        cohorts="c",
        llm_analyzed=True,
        archived=False,
        contains_pii=True,
    )
    yield "excluded: contains_spam True", comparison(
        [turn(user_msg(), llm_msg("a", 10), llm_msg("b", 10))],
        cohorts="c",
        llm_analyzed=True,
        archived=False,
        contains_spam=True,
    )
    yield "kept: contains_pii False, contains_spam False", comparison(
        [turn(user_msg(), llm_msg("a", 10), llm_msg("b", 10))],
        cohorts="c",
        llm_analyzed=True,
        archived=False,
        contains_pii=False,
        contains_spam=False,
    )

    # voted_at set -> time_to_vote = voted_at - max(updated_at_a, updated_at_b).
    # llm_msg updated_at defaults to 12:00:03; vote at 12:00:10 -> 7.0s.
    yield "voted turn -> time_to_vote computed", comparison(
        [
            turn(
                user_msg("q"),
                llm_msg("a", 100),
                llm_msg("b", 200),
                "a_better",
                voted_at=datetime(2024, 1, 1, 12, 0, 10),
            )
        ],
        cohorts="c",
        llm_analyzed=True,
        archived=False,
    )

    # voted_at set but one side never answered -> no "both finished" moment, so
    # time_to_vote must be None (not computed off the single answer).
    yield "voted but b missing -> time_to_vote None", comparison(
        [
            turn(
                user_msg("q"),
                llm_msg("a", 70),
                None,
                "a_better",
                voted_at=datetime(2024, 1, 1, 12, 0, 10),
            )
        ],
        cohorts="c",
        llm_analyzed=True,
        archived=False,
    )

    yield "multi-turn, b missing in one turn -> totals None", comparison(
        [
            turn(user_msg(), llm_msg("a1", 100), llm_msg("b1", 100)),
            turn(user_msg(), llm_msg("a2", 100), None),
        ],
        cohorts="c",
        llm_analyzed=True,
        archived=False,
    )


# --- cases the old pipeline skipped (both must raise) ----------------------


def skip_cases():
    # Known llm + tokens None -> conso math raises TypeError -> comparison
    # dropped. This is the actual (incidental) skip behaviour of the old code.
    yield "known llm + tokens None", comparison(
        [turn(user_msg(), llm_msg("a", tokens=None), llm_msg("b", 10))],
    )
    # Present message with a missing timestamp -> latency math raises.
    yield "llm missing responded_at", comparison(
        [turn(user_msg(), llm_msg("a", 10, responded_at=None), llm_msg("b", 10))],
    )
    # User message with no content -> UserMessageRead validation fails.
    yield "user message content None", comparison(
        [turn(user_msg(content=None), llm_msg("a", 10), llm_msg("b", 10))],
    )


# --- runner ----------------------------------------------------------------


def _raises(fn, comp):
    try:
        fn(comp)
        return False
    except Exception:
        return True


def time_to_vote_value_cases():
    # (name, comparison, expected time_to_vote). Pins the actual value, because
    # equivalence alone can't catch a bug that lives in both code paths.
    both = comparison(
        [
            turn(
                user_msg("q"),
                llm_msg("a", 70),  # updated_at 12:00:03
                llm_msg("b", 80, updated_at=datetime(2024, 1, 1, 12, 0, 4)),
                "a_better",
                voted_at=datetime(2024, 1, 1, 12, 0, 10),
            )
        ],
        cohorts="c",
        llm_analyzed=True,
        archived=False,
    )
    one_sided = comparison(
        [
            turn(
                user_msg("q"),
                llm_msg("a", 70),
                None,
                "a_better",
                voted_at=datetime(2024, 1, 1, 12, 0, 10),
            )
        ],
        cohorts="c",
        llm_analyzed=True,
        archived=False,
    )
    no_vote = comparison(
        [turn(user_msg("q"), llm_msg("a", 70), llm_msg("b", 80))],
        cohorts="c",
        llm_analyzed=True,
        archived=False,
    )
    # both finished (later of 12:00:03 / 12:00:04) -> vote at 12:00:10 -> 6.0s
    yield "both answered + voted", both, 6.0
    yield "one side missing + voted", one_sided, None
    yield "both answered, no vote", no_vote, None


def run():
    failures = []

    for name, comp in equivalent_cases():
        expected = oracle_comparison_to_turns(comp)
        actual = comparison_to_turns(comp)
        if actual != expected:
            failures.append(f"[VALUE] {name}")
            for i, (a, e) in enumerate(zip(actual, expected)):
                for k in set(a) | set(e):
                    if a.get(k) != e.get(k):
                        print(f"    DIFF row{i}.{k}: new={a.get(k)!r} old={e.get(k)!r}")
        elif [list(r) for r in actual] != [list(r) for r in expected]:
            failures.append(f"[KEY-ORDER] {name}")
        else:
            print(f"  ok  {name}  ({len(actual)} rows)")

    for name, comp in skip_cases():
        o, n = _raises(oracle_comparison_to_turns, comp), _raises(
            comparison_to_turns, comp
        )
        if not (o and n):
            failures.append(f"[SKIP oracle={o} new={n}] {name}")
        else:
            print(f"  ok  skip: {name}")

    for name, comp, expected in time_to_vote_value_cases():
        got = comparison_to_turns(comp)[0]["metadata"]["time_to_vote"]
        if got != expected:
            failures.append(f"[TIME_TO_VOTE {name}] got {got!r}, expected {expected!r}")
        else:
            print(f"  ok  time_to_vote: {name}  ({got!r})")

    print()
    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print("   -", f)
        sys.exit(1)
    print("All equivalence cases passed.")


# pytest entry points
def test_equivalence():
    for name, comp in equivalent_cases():
        assert comparison_to_turns(comp) == oracle_comparison_to_turns(comp), name


def test_skips():
    for name, comp in skip_cases():
        assert _raises(comparison_to_turns, comp), name


def test_time_to_vote_values():
    for name, comp, expected in time_to_vote_value_cases():
        got = comparison_to_turns(comp)[0]["metadata"]["time_to_vote"]
        assert got == expected, f"{name}: got {got!r}, expected {expected!r}"


if __name__ == "__main__":
    run()
