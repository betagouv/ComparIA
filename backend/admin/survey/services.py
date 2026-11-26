import re
import unicodedata
import uuid

from sqlalchemy import String, cast
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, true
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.survey.services import (
    SurveyOptionUnknownError,
    SurveyQuestionNotFoundError,
)
from utils.database.models.survey import (
    AdminSurveyOption,
    AdminSurveyQuestion,
    AdminSurveyResponse,
    SurveyAnswer,
    SurveyOption,
    SurveyOptionWrite,
    SurveyPromptLog,
    SurveyQuestion,
    SurveyQuestionCreate,
    SurveyQuestionOrder,
    SurveyQuestionUpdate,
)
from utils.database.models.utils import utc_now
from utils.storage.redis import REDIS_SURVEY_KEY, invalidate_cache


class SurveyQuestionInUseError(Exception):
    """Answers already carry this question, so it is archived rather than deleted."""


class SurveyQuestionLabelUnusableError(Exception):
    """A label with no letters or digits leaves nothing to build a key from."""


class SurveyQuestionKeyCollisionError(Exception):
    """
    A label that slugs to a key another question already uses. Distinct from
    `SurveyQuestionLabelUnusableError`: the label itself is fine, the admin
    just needs to reword it so it stops colliding.
    """


class SurveyOrderMismatchError(Exception):
    """An order has to list every question exactly once, and nothing else."""


def _key(label: str) -> str:
    """
    Derive a stable, ascii, column-safe key from a label. Copied from
    `backend/vote_tags/services.py::_tag_key` in spirit: question keys and
    option keys both work the same way.
    """
    # Only the accents are dropped; every other character outside [a-z0-9],
    # typographic apostrophes included, separates words. The admin form
    # previews the key with this same rule (`slug` in
    # frontend/src/routes/(admin)/admin/survey/+page.svelte), so the two must
    # change together.
    normalized = re.sub(
        r"[\u0300-\u036f]", "", unicodedata.normalize("NFKD", label)
    ).lower()
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")[:100]


def _respondent_expr():
    """One value per respondent across both ownership columns, for counting
    distinct respondents in SQL. A user id and an anonymous hash never look
    alike, so the two cannot collide."""
    return func.coalesce(
        cast(col(SurveyAnswer.user_id), String), col(SurveyAnswer.anonymous_user_hash)
    )


async def admin_list(session: AsyncSession) -> AdminSurveyResponse:
    def select_count_query(question_id: uuid):
        return (
            select(SurveyAnswer.value, func.count())
            .where(SurveyAnswer.question_id == question_id)
            .group_by(col(SurveyAnswer.value))
        )

    def checkbox_group_count_query(question_id: uuid):
        item = (
            func.jsonb_array_elements_text(SurveyAnswer.value)
            .table_valued("value")
            .lateral("item")
        )

        return (
            select(item.c.value, func.count())
            .where(SurveyAnswer.question_id == question_id)
            .select_from(SurveyAnswer)
            .join(item, true())
            .group_by(item.c.value)
        )

    questions = list(
        (
            await session.exec(
                select(SurveyQuestion).order_by(col(SurveyQuestion.display_order))
            )
        ).all()
    )

    respondent_counts: dict[uuid.UUID, int] = dict(
        (
            await session.exec(
                select(
                    SurveyAnswer.question_id,
                    func.count(func.distinct(_respondent_expr())),
                ).group_by(col(SurveyAnswer.question_id))
            )
        ).all()
    )
    total_respondents = (
        await session.exec(select(func.count(func.distinct(_respondent_expr()))))
    ).one()

    admin_questions = []
    for question in questions:
        # Counted in the database: the answer table grows with every respondent,
        # and this runs on every admin read and after every admin write.
        counts = {
            v: count
            for v, count in (
                await session.exec(
                    select_count_query(question.id)
                    if question.input_type == "select"
                    else checkbox_group_count_query(question.id)
                )
            ).all()
        }
        options = [
            AdminSurveyOption(
                key=option.key,
                labels=option.labels,
                archived=option.archived,
                answer_count=counts.get(option.key, 0),
            )
            for option in (SurveyOption.model_validate(raw) for raw in question.options)
        ]

        admin_questions.append(
            AdminSurveyQuestion(
                id=question.id,
                key=question.key,
                required=question.required,
                input_type=question.input_type,
                labels=question.labels,
                options=options,
                published=question.published,
                revision=question.revision,
                display_order=question.display_order,
                archived=question.archived_at is not None,
                respondent_count=respondent_counts.get(question.id, 0),
            )
        )

    return AdminSurveyResponse(
        questions=admin_questions,
        total_respondents=total_respondents,
    )


def _derive_option_keys(options: list[SurveyOptionWrite]) -> list[SurveyOption]:
    used: set[str] = set()
    result = []
    for option in options:
        base = _key(next(iter(option.labels.values())))
        if not base:
            raise SurveyQuestionLabelUnusableError()
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}_{suffix}"
            suffix += 1
        used.add(candidate)
        result.append(
            SurveyOption(
                key=candidate, labels=dict(option.labels), archived=option.archived
            )
        )
    return result


async def create_question(
    session: AsyncSession, payload: SurveyQuestionCreate
) -> SurveyQuestion:
    key = _key(next(iter(payload.labels.values())))
    if not key:
        raise SurveyQuestionLabelUnusableError()

    max_order = (
        await session.exec(select(func.max(SurveyQuestion.display_order)))
    ).one()

    options = _derive_option_keys(payload.options)

    question = SurveyQuestion(
        key=key,
        required=payload.required,
        input_type=payload.input_type,
        labels=dict(payload.labels),
        options=[option.model_dump() for option in options],
        published=payload.published,
        display_order=0 if max_order is None else max_order + 1,
    )
    session.add(question)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        # The key is the only unique constraint on this table, so a collision
        # here means the label slugs to a key another question already uses —
        # not that the label is unusable, which was checked before the insert.
        raise SurveyQuestionKeyCollisionError() from error

    invalidate_cache(REDIS_SURVEY_KEY)
    await session.refresh(question)
    return question


async def update_question(
    session: AsyncSession, question_id: uuid.UUID, payload: SurveyQuestionUpdate
) -> SurveyQuestion:
    """
    Labels and option labels are freely editable; `key` never changes, on the
    question or on any option. Options sent with a key keep it, options sent
    without one are new. Options missing from the payload are archived, never
    dropped, because answers already point at them.
    """
    question = await session.get(SurveyQuestion, question_id)
    if question is None:
        raise SurveyQuestionNotFoundError()

    existing = [SurveyOption.model_validate(raw) for raw in question.options]
    existing_by_key = {option.key: option for option in existing}
    old_live_keys = {option.key for option in existing if not option.archived}

    label_changed = question.labels != dict(payload.labels)

    seen_keys: set[str] = set()
    used_keys: set[str] = set(existing_by_key)
    new_options: list[SurveyOption] = []

    for incoming in payload.options:
        if incoming.key:
            if incoming.key not in existing_by_key:
                raise SurveyOptionUnknownError(incoming.key)
            key = incoming.key
            if dict(incoming.labels) != existing_by_key[key].labels:
                label_changed = True
        else:
            base = _key(next(iter(incoming.labels.values())))
            if not base:
                raise SurveyQuestionLabelUnusableError()
            candidate = base
            suffix = 2
            while candidate in used_keys:
                candidate = f"{base}_{suffix}"
                suffix += 1
            key = candidate
            used_keys.add(key)
            label_changed = True

        seen_keys.add(key)
        new_options.append(
            SurveyOption(
                key=key, labels=dict(incoming.labels), archived=incoming.archived
            )
        )

    for key, option in existing_by_key.items():
        if key not in seen_keys:
            new_options.append(
                SurveyOption(key=key, labels=option.labels, archived=True)
            )

    new_live_keys = {option.key for option in new_options if not option.archived}
    live_set_changed = new_live_keys != old_live_keys

    question.labels = dict(payload.labels)
    question.options = [option.model_dump() for option in new_options]
    question.published = payload.published
    # Neither of these changes what an answer means, so neither bumps the
    # revision: the same wording asked in one more place is the same column.
    question.required = payload.required
    if label_changed or live_set_changed:
        question.revision += 1
    question.updated_at = utc_now()

    session.add(question)
    await session.commit()
    invalidate_cache(REDIS_SURVEY_KEY)
    await session.refresh(question)
    return question


async def set_archived(
    session: AsyncSession, question_id: uuid.UUID, archived: bool, admin_id: uuid.UUID
) -> SurveyQuestion:
    question = await session.get(SurveyQuestion, question_id)
    if question is None:
        raise SurveyQuestionNotFoundError()

    # archived_at is the survey's own column and reads in UTC like every other
    # one it owns; updated_at is stamped on the same scale so a row's own two
    # stamps stay comparable.
    question.archived_at = utc_now() if archived else None
    question.archived_by = admin_id if archived else None
    question.updated_at = utc_now()
    session.add(question)
    await session.commit()
    invalidate_cache(REDIS_SURVEY_KEY)
    await session.refresh(question)
    return question


async def delete_question(session: AsyncSession, question_id: uuid.UUID) -> None:
    """Deletes a question nobody has answered. Once an answer carries it the
    row is archived instead: the admin layer maps `SurveyQuestionInUseError`
    onto that."""
    question = await session.get(SurveyQuestion, question_id)
    if question is None:
        raise SurveyQuestionNotFoundError()

    count = (
        await session.exec(
            select(func.count(col(SurveyAnswer.id))).where(
                SurveyAnswer.question_id == question_id
            )
        )
    ).one()
    if count:
        raise SurveyQuestionInUseError()

    await session.execute(
        sa_delete(SurveyPromptLog).where(SurveyPromptLog.question_id == question_id)
    )
    await session.delete(question)
    await session.commit()
    invalidate_cache(REDIS_SURVEY_KEY)


async def reorder(session: AsyncSession, payload: SurveyQuestionOrder) -> None:
    """Write the order from the list the client sends. It has to name every
    question exactly once, so a stale page cannot drop a question another
    admin added in the meantime."""
    siblings = list((await session.exec(select(SurveyQuestion))).all())
    by_id = {row.id: row for row in siblings}
    if len(payload.ids) != len(by_id) or set(payload.ids) != set(by_id):
        raise SurveyOrderMismatchError()

    for position, question_id in enumerate(payload.ids):
        row = by_id[question_id]
        row.display_order = position
        session.add(row)

    await session.commit()
    invalidate_cache(REDIS_SURVEY_KEY)
