"""The admin activity panel, against a real Postgres.

Skipped where Postgres is not installed.
"""

import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "RAW")

# The filter options import the actions package, which declares a legacy
# table: load it before the test cluster is built, or later tests truncate a
# table that was never created.
import utils.database.actions  # noqa: E402, F401
from backend.activity import services  # noqa: E402
from backend.activity.models import (  # noqa: E402
    ActivityFilters,
    ConversationFilters,
)
from utils.database import session as session_module  # noqa: E402
from utils.database.models import (  # noqa: E402
    Comparison,
    LLMMessage,
    Turn,
    UserMessage,
)

# An hour back, so a second prompt a minute later is still in the past.
NOW = datetime.now() - timedelta(hours=1)


@pytest.fixture
def activity(database, monkeypatch):
    """The database runner, with the panel's own engine reset around each
    scenario and no Redis."""
    monkeypatch.setattr(session_module, "_activity_engine", None)
    redis = Mock()
    redis.get.return_value = None
    monkeypatch.setattr(services, "get_redis_client", lambda: redis)

    def run(scenario):
        async def wrapped():
            try:
                return await scenario()
            finally:
                if session_module._activity_engine is not None:
                    await session_module._activity_engine.dispose()
                    session_module._activity_engine = None

        return database(wrapped)

    return run


async def add_llms() -> tuple[uuid.UUID, uuid.UUID]:
    from sqlalchemy import text

    a, b, lab, license = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with session_module.get_session() as session:
        await session.execute(
            text(
                "INSERT INTO llm_lab (id, created_at, updated_at, name, origin_country)"
                " VALUES (:id, now(), now(), 'Lab', 'FR')"
            ),
            {"id": lab},
        )
        await session.execute(
            text(
                "INSERT INTO llm_license (id, created_at, updated_at, kind, name,"
                " reuse, commercial_use) VALUES (:id, now(), now(), 'open', 'MIT',"
                " true, true)"
            ),
            {"id": license},
        )
        for id, name in ((a, "Alpha"), (b, "Beta")):
            await session.execute(
                text(
                    "INSERT INTO llm_data (id, created_at, updated_at, lab_id,"
                    " license_id, human_id, status, name, rate_limited,"
                    " release_date, arch, params, inputs, public_weights,"
                    " public_training_data, public_training_code, eu_hostable,"
                    " price_in, price_out, links) VALUES (:id, now(), now(), :lab,"
                    " :license, :human_id, 'enabled', :name, false, '2025-01-01',"
                    " 'dense', 7, '[\"text\"]', true, false, false, true, 0, 0,"
                    " '[]')"
                ),
                {
                    "id": id,
                    "lab": lab,
                    "license": license,
                    "human_id": name.lower(),
                    "name": name,
                },
            )
        await session.commit()
    return a, b


async def add_comparison(
    llms: tuple[uuid.UUID, uuid.UUID],
    *,
    created_at: datetime = NOW,
    prompts: list[str] = ["Bonjour"],
    choice: str | None = None,
    comment: str | None = None,
    tags: list[str] = [],
    **fields,
) -> uuid.UUID:
    comparison_id = uuid.uuid4()
    async with session_module.get_session() as session:
        session.add(
            Comparison(
                id=comparison_id,
                created_at=created_at,
                updated_at=created_at,
                ip="203.0.113.7",
                mode=fields.pop("mode", "random"),
                llm_id_a=llms[0],
                llm_id_b=llms[1],
                archived=fields.pop("archived", False),
                **fields,
            )
        )
        await session.flush()
        for index, prompt in enumerate(prompts):
            at = created_at + timedelta(minutes=index)
            messages = [
                LLMMessage(
                    created_at=at,
                    responded_at=at + timedelta(seconds=3),
                    updated_at=at,
                    content=f"Réponse {side}",
                    generation_id="test",
                    tokens=12,
                    is_cached=False,
                )
                for side in "ab"
            ]
            session.add_all(messages)
            await session.flush()
            turn = Turn(
                comparison_id=comparison_id,
                created_at=at,
                updated_at=at,
                llm_msg_a_id=messages[0].id,
                llm_msg_b_id=messages[1].id,
                choice=choice if index == 0 else None,
                keyword_annotations_a=tags if index == 0 else [],
                custom_annotation_a=comment if index == 0 else None,
            )
            session.add(turn)
            await session.flush()
            session.add(UserMessage(created_at=at, content=prompt, turn_id=turn.id))
        await session.commit()
    return comparison_id


def test_overview_counts_the_period(activity):
    async def scenario():
        llms = await add_llms()
        await add_comparison(
            llms, prompts=["Un", "Deux"], choice="a_better", tags=["useful"]
        )
        await add_comparison(llms, choice="idk", comment="Bof")
        await add_comparison(llms, revealed=True, mode="custom")
        # Outside the default 30 days, and archived: neither counts.
        await add_comparison(llms, created_at=NOW - timedelta(days=60))
        await add_comparison(llms, archived=True, choice="b_better")
        return await services.get_overview(ActivityFilters())

    overview = activity(scenario)

    assert overview.bucket == "day"
    assert overview.totals.conversations == 3
    assert overview.totals.prompts == 4
    assert overview.totals.votes == 1
    assert overview.totals.idk == 1
    assert overview.totals.comments == 1
    assert overview.totals.tagged == 1
    assert overview.totals.voted_conversations == 1
    assert overview.totals.revealed_conversations == 1
    assert overview.modes == {"random": 2, "custom": 1}
    assert overview.choices == {"a_better": 1, "idk": 1, "none": 2}
    assert len(overview.activity) == 30
    assert sum(point.conversations for point in overview.activity) == 3
    assert sum(point.prompts for point in overview.activity) == 4
    assert sum(point.votes for point in overview.activity) == 1
    assert overview.activity[-1].partial
    assert not overview.activity[0].partial


def test_overview_can_include_archived_and_narrow_to_a_model(activity):
    async def scenario():
        llms = await add_llms()
        await add_comparison(llms)
        await add_comparison(llms, archived=True)
        archived = await services.get_overview(ActivityFilters(include_archived=True))
        other_model = await services.get_overview(ActivityFilters(llm_id=uuid.uuid4()))
        return archived, other_model

    archived, other_model = activity(scenario)

    assert archived.totals.conversations == 2
    assert other_model.totals.conversations == 0


def test_the_list_pages_newest_first_without_repeating_a_row(activity):
    async def scenario():
        llms = await add_llms()
        ids = [
            await add_comparison(llms, created_at=NOW - timedelta(hours=hours))
            for hours in range(5)
        ]
        pages = [await services.list_conversations(ConversationFilters(limit=2))]
        while pages[-1].next_cursor:
            pages.append(
                await services.list_conversations(
                    ConversationFilters(limit=2, cursor=pages[-1].next_cursor)
                )
            )
        return ids, pages

    ids, pages = activity(scenario)

    assert [len(page.items) for page in pages] == [2, 2, 1]
    assert [row.id for page in pages for row in page.items] == ids
    assert pages[0].total == 5
    assert pages[1].total is None
    row = pages[0].items[0]
    assert row.model_a is not None and row.model_a.name == "Alpha"
    assert row.first_prompt == "Bonjour"


def test_the_list_filters_on_what_was_said_and_how_it_was_voted(activity):
    async def scenario():
        llms = await add_llms()
        wanted = await add_comparison(
            llms, prompts=["Une recette de crêpes ?"], choice="a_better", comment="Top"
        )
        flagged = await add_comparison(
            llms, archived=True, contains_pii=True, archived_reason="pii"
        )
        revealed = await add_comparison(llms, prompts=["Autre chose"], revealed=True)

        async def ids(**filters):
            page = await services.list_conversations(ConversationFilters(**filters))
            return [row.id for row in page.items]

        return (
            wanted,
            flagged,
            (await services.list_conversations(ConversationFilters())).items,
            await ids(search="CRÊPES"),
            await ids(search="cr%pes"),
            await ids(has_comment=True),
            await ids(choice="a_better"),
            await ids(has_vote=False),
            await ids(flag="pii"),
            revealed,
            await ids(revealed=True),
        )

    (
        wanted,
        flagged,
        rows,
        by_search,
        by_wildcard,
        by_comment,
        by_choice,
        unvoted,
        by_pii,
        revealed,
        by_revealed,
    ) = activity(scenario)

    row = next(row for row in rows if row.id == wanted)
    assert row.comment == "Top"
    assert by_search == [wanted]
    assert by_wildcard == []
    assert by_comment == [wanted]
    assert by_choice == [wanted]
    assert wanted not in unvoted and len(unvoted) == 1
    # Flagged conversations are archived: asking for them brings them back.
    assert by_pii == [flagged]
    assert by_revealed == [revealed]


def test_a_conversation_reads_in_full_without_who_wrote_it(activity):
    async def scenario():
        llms = await add_llms()
        comparison_id = await add_comparison(
            llms, prompts=["Un", "Deux"], choice="b_better", tags=["useful"]
        )
        return await services.get_conversation(comparison_id)

    conversation = activity(scenario)

    assert conversation is not None
    assert [turn.prompt for turn in conversation.turns] == ["Un", "Deux"]
    first = conversation.turns[0]
    assert first.choice == "b_better"
    assert first.tags_a == ["useful"]
    assert first.answer_a is not None and first.answer_a.duration_ms == 3000
    dumped = conversation.model_dump_json()
    assert "203.0.113.7" not in dumped
    assert "visitor_id" not in dumped


def test_the_filter_options_list_models_and_cohorts(activity):
    async def scenario():
        llms = await add_llms()
        await add_comparison(llms, cohorts="pix")
        await add_comparison(llms)
        return await services.get_filter_options()

    options = activity(scenario)

    assert [llm.name for llm in options.llms] == ["Alpha", "Beta"]
    assert options.cohorts == ["pix"]
    assert "Law & Justice" in options.categories


def test_a_bad_cursor_is_refused():
    with pytest.raises(services.InvalidCursorError):
        services.decode_cursor("not-a-cursor")


@pytest.mark.parametrize(
    ("filters", "bucket"),
    [
        (ActivityFilters(period="24h"), "hour"),
        (ActivityFilters(period="30d"), "day"),
        (ActivityFilters(period="365d"), "week"),
        (ActivityFilters(period="all"), "month"),
    ],
)
def test_the_period_picks_its_bucket(filters, bucket):
    assert services.resolve_range(filters, NOW)[2] == bucket


def test_custom_dates_include_the_last_day():
    start, end, _ = services.resolve_range(
        ActivityFilters(
            start=datetime(2026, 9, 1).date(), end=datetime(2026, 9, 30).date()
        ),
        NOW,
    )

    assert start == datetime(2026, 9, 1)
    assert end == datetime(2026, 10, 1)
