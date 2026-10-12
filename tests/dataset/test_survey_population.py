"""
Which survey answers the export reads, against a throwaway Postgres: only
those of respondents who own a comparison the open dataset keeps, so the
five-respondent rule counts the people a release actually shows.

Run with pytest:
    uv run --group dev --group data pytest tests/dataset/test_survey_population.py
"""

import uuid

from sqlalchemy import text

from utils.database.models import Comparison, SurveyAnswer, SurveyQuestion
from utils.database.models.utils import utc_now
from utils.database.session import get_session
from utils.dataset.compute import _survey_answers_query

TERMS = "v1"


def published_comparison(**owner) -> Comparison:
    return Comparison(
        ip="192.0.2.10",
        mode="random",
        llm_id_a=uuid.uuid4(),
        llm_id_b=uuid.uuid4(),
        llm_analyzed=True,
        contains_pii=False,
        contains_spam=False,
        archived=False,
        **owner,
    )


def answer(question_id: uuid.UUID, **owner) -> SurveyAnswer:
    return SurveyAnswer(
        question_id=question_id,
        value="a",
        terms_version=TERMS,
        answered_at=utc_now(),
        **owner,
    )


async def respondents_read_by_the_export(rows) -> set[str]:
    async with get_session() as session:
        # The comparisons and answers point at no LLM and no account: skip the
        # foreign keys rather than build what the query never reads.
        await session.execute(text("SET session_replication_role = replica"))
        for row in rows:
            session.add(row)
        await session.commit()
        result = await session.exec(_survey_answers_query({TERMS}))
        return {
            str(user_id) if user_id else anonymous_user_hash
            for _, _, user_id, anonymous_user_hash, _ in result.all()
        }


def test_only_respondents_with_a_published_comparison_are_read(database):
    question = SurveyQuestion(
        key="age",
        input_type="select",
        labels={"fr": "Âge"},
        options=[
            {"key": "a", "labels": {"fr": "A"}},
            {"key": "b", "labels": {"fr": "B"}},
        ],
        published=True,
    )
    published_user, silent_user = uuid.uuid4(), uuid.uuid4()
    archived = published_comparison(anonymous_user_hash="held-back")
    archived.archived = True

    async def scenario():
        return await respondents_read_by_the_export(
            [
                question,
                published_comparison(user_id=published_user),
                published_comparison(anonymous_user_hash="published"),
                archived,
                # Signed in after this comparison: it stays the account's,
                # not the session's, once the user id is on it.
                published_comparison(
                    user_id=published_user, anonymous_user_hash="claimed"
                ),
                answer(question.id, user_id=published_user),
                answer(question.id, user_id=silent_user),
                answer(question.id, anonymous_user_hash="published"),
                answer(question.id, anonymous_user_hash="held-back"),
                answer(question.id, anonymous_user_hash="claimed"),
                answer(question.id, anonymous_user_hash="never-chatted"),
            ]
        )

    assert database(scenario) == {str(published_user), "published"}
