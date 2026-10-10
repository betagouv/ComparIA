import re
import unicodedata
import uuid
from datetime import timedelta
from typing import Annotated, Literal

from pydantic import BeforeValidator, ConfigDict, create_model
from sqlalchemy import String, cast
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, true
from sqlalchemy import update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.database.models.survey import (
    MAX_QUESTION_PROMPTS,
    AdminSurveyOption,
    AdminSurveyQuestion,
    AdminSurveyResponse,
    MySurveyAnswer,
    PublicSurveyOption,
    PublicSurveyQuestion,
    SurveyAnswer,
    SurveyAnswerSubmit,
    SurveyAnswerValue,
    SurveyOption,
    SurveyOptionWrite,
    SurveyPromptLog,
    SurveyQuestion,
    SurveyQuestionAnswer,
    SurveyQuestionCreate,
    SurveyQuestionOrder,
    SurveyQuestionUpdate,
)
from utils.database.models.utils import utc_now
from utils.database.session import get_session
from utils.database.settings import get_app_settings
from utils.storage.redis import REDIS_SURVEY_KEY, invalidate_cache, redis_cache


class SurveyQuestionNotFoundError(Exception):
    pass


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


class SurveyOptionUnknownError(Exception):
    """
    A key that is not a live option on the question (submitting an answer), or
    not one of the question's existing options at all (editing one).
    """


class SurveyOrderMismatchError(Exception):
    """An order has to list every question exactly once, and nothing else."""


# --- shared helpers -------------------------------------------------------


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


def _label(labels: dict[str, str], locale: str, default_locale: str) -> str:
    """Exact locale, then the instance default, then whatever is there."""
    if locale in labels:
        return labels[locale]
    return labels.get(default_locale) or next(iter(labels.values()))


async def _default_locale() -> str:
    """Read once per request and handed down: every label on a page falls back
    to it, and each read of the settings is a round trip to Redis."""
    return (await get_app_settings()).default_locale


def _require_respondent(
    user_id: uuid.UUID | None, anonymous_user_hash: str | None
) -> None:
    if (user_id is None) == (anonymous_user_hash is None):
        raise ValueError("exactly one of user_id or anonymous_user_hash must be set")


def _respondent_clause(
    model, user_id: uuid.UUID | None, anonymous_user_hash: str | None
):
    """`WHERE` fragment picking one respondent's rows on a table shaped like
    `SurveyAnswer` / `SurveyPromptLog` (both carry the same two columns)."""
    if user_id is not None:
        return col(model.user_id) == user_id
    return col(model.anonymous_user_hash) == anonymous_user_hash


@redis_cache(REDIS_SURVEY_KEY)
async def _all_questions() -> list[SurveyQuestion]:
    """
    Every question, archived ones included, in display order. Cached the way
    `vote_tags` caches its full tag list: question wording changes rarely, so
    one cached list serves every locale and every respondent.
    """
    async with get_session() as session:
        result = await session.exec(
            select(SurveyQuestion).order_by(col(SurveyQuestion.display_order))
        )
        return list(result.all())


async def _askable_questions() -> list[SurveyQuestion]:
    return sorted(
        (
            question
            for question in await _all_questions()
            if question.archived_at is None
        ),
        key=lambda question: question.display_order,
    )


async def _all_answers(
    user_id: uuid.UUID | None, anonymous_user_hash: str | None
) -> list[SurveyAnswer]:
    """Get all survey answers from user or anonymous."""
    _require_respondent(user_id, anonymous_user_hash)

    async with get_session() as session:
        return (
            await session.exec(
                select(SurveyAnswer).where(
                    _respondent_clause(SurveyAnswer, user_id, anonymous_user_hash)
                )
            )
        ).all()


async def _all_logs(
    user_id: uuid.UUID | None,
    anonymous_user_hash: str | None,
    question_ids: set[uuid.UUID] | None = None,
) -> list[SurveyPromptLog]:
    query = select(SurveyPromptLog).where(
        _respondent_clause(SurveyPromptLog, user_id, anonymous_user_hash)
    )
    if question_ids:
        query = query.where(col(SurveyPromptLog.question_id).in_(question_ids))

    async with get_session() as session:
        return (await session.exec(query)).all()


def _to_public(
    question: SurveyQuestion,
    locale: str,
    default_locale: str,
    *,
    include_archived: bool = False,
) -> PublicSurveyQuestion:
    options = []
    for raw in question.options:
        option = SurveyOption.model_validate(raw)
        if option.archived and not include_archived:
            continue
        options.append(
            PublicSurveyOption(
                key=option.key,
                label=_label(option.labels, locale, default_locale),
                archived=option.archived,
            )
        )
    return PublicSurveyQuestion(
        id=question.id,
        key=question.key,
        required=question.required,
        input_type=question.input_type,
        label=_label(question.labels, locale, default_locale),
        revision=question.revision,
        options=options,
    )


# --- public ----------------------------------------------------------------


async def list_questions(locale: str) -> list[PublicSurveyQuestion]:
    """
    Returns every askable questions.
    """
    default_locale = await _default_locale()
    return [
        _to_public(question, locale, default_locale)
        for question in await _askable_questions()
    ]


async def list_unanswered_questions_ids(
    locale: str,
    user_id: uuid.UUID | None,
    anonymous_user_hash: str | None,
) -> list[uuid.UUID]:
    """
    Returns unanswered questions ids so the client can choose which to show depending on
    context. Those are questions that never have been seen, not over-shown or not shown
    too recently.
    """
    questions = await _askable_questions()
    questions_logs = {
        log.question_id: log for log in await _all_logs(user_id, anonymous_user_hash)
    }
    async with get_session() as session:
        answered_ids = set(
            (
                await session.exec(
                    select(SurveyAnswer.question_id).where(
                        _respondent_clause(SurveyAnswer, user_id, anonymous_user_hash)
                    )
                )
            ).all()
        )

    reask_after_days = (await get_app_settings()).survey_reask_after_days
    cutoff = utc_now() - timedelta(days=reask_after_days)

    never_answered_ids = set()
    for question in questions:
        if question.id in answered_ids:
            continue
        log = questions_logs.get(question.id)
        if log is not None:
            if log.shown_count >= MAX_QUESTION_PROMPTS:
                continue
            if log.last_shown_at is not None and log.last_shown_at > cutoff:
                continue
        never_answered_ids.add(question.id)

    return list(never_answered_ids)


def _validate_answers(
    questions: list[SurveyQuestion],
    answers: list[SurveyQuestionAnswer],
    previous_answers: dict[uuid.UUID, SurveyAnswerValue],
    ignore_required: bool = False,
):
    """
    Validate survey answers against a dynamic pydantic model.
    """
    parse_nonish = BeforeValidator(lambda v: None if v is None or not len(v) else v)

    def get_question_type(question: SurveyQuestion):
        if question.input_type in ("select", "checkbox_group"):
            previous_answer = previous_answers.get(question.id, [])
            if question.input_type == "select" and previous_answer:
                previous_answer = [previous_answer]

            # Dynamic literal to properly check answer is an accepted value
            base_type = Literal[
                tuple(
                    [
                        option.key
                        for option in (
                            SurveyOption.model_validate(raw) for raw in question.options
                        )
                        # Special case:
                        # An option archived since it was chosen stops being offered, but the
                        # person who holds it can keep it: saving the profile page untouched
                        # sends it straight back, and that must not fail or drop the answer.
                        if not option.archived or option.key in previous_answer
                    ]
                )
            ]
            if question.input_type == "checkbox_group":
                return list[base_type]
            return base_type
        else:
            raise NotImplementedError(
                f"Unknow survey question 'input_type': '{question.input_type}'."
            )

    def get_annotation(question: SurveyQuestion):
        required = not ignore_required and question.required
        type_ = get_question_type(question)
        if not required:
            type_ = type_ | None
        type_ = Annotated[type_, parse_nonish]
        return type_ if required else (type_, None)

    SurveyModel = create_model(
        "SurveyModel",
        **{str(question.id): get_annotation(question) for question in questions},
        __config__=ConfigDict(extra="forbid"),
    )

    return SurveyModel(**{str(answer.question_id): answer.value for answer in answers})


async def submit_answers(
    session: AsyncSession,
    payload: SurveyAnswerSubmit,
    user_id: uuid.UUID | None,
    anonymous_user_hash: str | None,
    terms_version: str | None,
) -> None:
    """
    Replace semantics: each question's answer fully replaces whatever this
    respondent answered before and add a log for not answered questions.
    """
    now = utc_now()
    question_ids = set([answer.question_id for answer in payload.answers])
    previous_answers = {
        answer.question_id: answer.value
        for answer in await _all_answers(user_id, anonymous_user_hash)
        if answer.question_id in question_ids
    }
    questions = [
        question
        for question in await _all_questions()
        if question.archived_at is None and question.id in question_ids
    ]
    logs = {
        log.question_id: log
        for log in await _all_logs(
            user_id, anonymous_user_hash, question_ids=question_ids
        )
    }

    answers = _validate_answers(
        questions, payload.answers, previous_answers, ignore_required=user_id is None
    )

    for question in questions:
        value = getattr(answers, str(question.id))
        log = logs.get(question.id)

        await session.execute(
            sa_delete(SurveyAnswer)
            .where(SurveyAnswer.question_id == question.id)
            .where(_respondent_clause(SurveyAnswer, user_id, anonymous_user_hash))
        )

        if value:
            session.add(
                SurveyAnswer(
                    question_id=question.id,
                    value=value,
                    user_id=user_id,
                    anonymous_user_hash=anonymous_user_hash,
                    question_revision=question.revision,
                    terms_version=terms_version,
                    answered_at=now,
                )
            )
            if log:
                # Remove previous not answered log
                await session.execute(
                    sa_delete(SurveyPromptLog).where(SurveyPromptLog.id == log.id)
                )
        else:
            # Record that the question has been asked but not answered
            if log is None:
                log = SurveyPromptLog(
                    question_id=question.id,
                    user_id=user_id,
                    anonymous_user_hash=anonymous_user_hash,
                    shown_count=1,
                    last_shown_at=now,
                )
            else:
                log.shown_count += 1
                log.last_shown_at = now

            session.add(log)


async def my_answers(
    locale: str,
    user_id: uuid.UUID | None,
    anonymous_user_hash: str | None,
) -> list[MySurveyAnswer]:
    """What the profile page and the personal-data export show: every question
    this respondent has answered, options included so an option archived since
    the answer was given still resolves to a label."""
    rows = await _all_answers(user_id, anonymous_user_hash)
    if not rows:
        return []

    selected: dict[uuid.UUID, SurveyAnswerValue] = {
        row.question_id: row.value for row in rows
    }

    questions_by_id = {question.id: question for question in await _all_questions()}
    default_locale = await _default_locale()

    results = []
    for question_id, value in selected.items():
        question = questions_by_id.get(question_id)
        if question is None:
            continue
        public = _to_public(question, locale, default_locale, include_archived=True)
        results.append(
            MySurveyAnswer(
                question_id=question.id,
                question_key=question.key,
                label=public.label,
                input_type=question.input_type,
                options=public.options,
                value=value,
                archived=question.archived_at is not None,
            )
        )
    return results


async def signup_questions_answered(
    user_id: uuid.UUID | None,
    anonymous_user_hash: str | None,
) -> bool:
    """
    Whether every required signup question has an answer from this respondent.

    Optional ones are asked on the same form and never hold anything up. A
    required one holds up every write to the arena (see
    `backend/survey/dependencies.py`), for new and existing accounts alike: a
    question made required later is put to existing users in a popup they
    can answer on the spot, so nobody is held anywhere they cannot answer.

    Opens its own session: it runs as a route guard before any work, and is
    free on the common path where nothing is configured.
    """
    signup_ids = [
        question.id for question in await _askable_questions() if question.required
    ]
    # The overwhelmingly common case is an instance with no required signup
    # questions at all, and it costs nothing: the question list is cached, so
    # the gate never reaches the database. Checked before the respondent, so
    # an instance with nothing configured answers the same either way.
    if not signup_ids:
        return True

    # A caller with no identity at all cannot have answered anything. Saying
    # so beats raising: this runs as a route guard, where an unexpected shape
    # should turn into the gate's own 428, not a 500.
    if user_id is None and anonymous_user_hash is None:
        return False
    _require_respondent(user_id, anonymous_user_hash)

    async with get_session() as session:
        answered_ids = set(
            (
                await session.exec(
                    select(SurveyAnswer.question_id)
                    .where(col(SurveyAnswer.question_id).in_(signup_ids))
                    .where(
                        _respondent_clause(SurveyAnswer, user_id, anonymous_user_hash)
                    )
                    .distinct()
                )
            ).all()
        )
    return set(signup_ids) <= answered_ids


async def carry_over_anonymous(
    session: AsyncSession, anonymous_user_hash: str, user_id: uuid.UUID
) -> None:
    """
    Reattach a visitor's anonymous answers and prompt history to the account
    they just signed into. Modelled on
    `_associate_anonymous_acceptance()` in `backend/auth/services.py`: this is
    called from inside that same transaction, so it never commits itself.
    """
    # Both sides can hold answers for the same question, since the login form
    # asks it of returning users too. The newer answer wins, per question: the
    # answer given a moment ago describes the person better than one given a
    # year ago. This is the same replace-in-place rule the profile page
    # follows, so the losing account rows go and the anonymous ones take
    # their place.
    just_answered = dict(
        (
            await session.exec(
                select(SurveyAnswer.question_id, SurveyAnswer.answered_at).where(
                    SurveyAnswer.anonymous_user_hash == anonymous_user_hash,
                    col(SurveyAnswer.user_id).is_(None),
                )
            )
        ).all()
    )
    if just_answered:
        account_answered = dict(
            (
                await session.exec(
                    select(SurveyAnswer.question_id, SurveyAnswer.answered_at).where(
                        SurveyAnswer.user_id == user_id,
                        col(SurveyAnswer.question_id).in_(list(just_answered)),
                    )
                )
            ).all()
        )
        # Ties go to the session: leaving both rows in place would trip the
        # unique index the moment the UPDATE below reassigns them.
        newer_on_the_session = [
            question_id
            for question_id, answered_at in just_answered.items()
            if question_id not in account_answered
            or answered_at >= account_answered[question_id]
        ]
        if newer_on_the_session:
            await session.execute(
                sa_delete(SurveyAnswer).where(
                    SurveyAnswer.user_id == user_id,
                    col(SurveyAnswer.question_id).in_(newer_on_the_session),
                )
            )
        # Where the account's answer is the newer one, the session's rows lose
        # and go. Reassigning them anyway would give the account two answers
        # to one question, or trip the unique index outright when both sides
        # chose the same option, and fail the sign-in with it.
        older_on_the_session = [
            question_id
            for question_id in just_answered
            if question_id not in newer_on_the_session
        ]
        if older_on_the_session:
            await session.execute(
                sa_delete(SurveyAnswer).where(
                    SurveyAnswer.anonymous_user_hash == anonymous_user_hash,
                    col(SurveyAnswer.user_id).is_(None),
                    col(SurveyAnswer.question_id).in_(older_on_the_session),
                )
            )

    await session.execute(
        sa_update(SurveyAnswer)
        .where(
            SurveyAnswer.anonymous_user_hash == anonymous_user_hash,
            SurveyAnswer.user_id.is_(None),
        )
        .values(user_id=user_id, anonymous_user_hash=None)
    )

    # The prompt log cannot simply be reassigned the way the answers are. Both
    # sides can hold a row for the same question, and the readers key their
    # lookup on question_id alone, so a second row would quietly win and hand
    # the respondent back showings they had already used up. Fold the two
    # counts together instead, then drop the anonymous row.
    anonymous_logs = (
        await session.exec(
            select(SurveyPromptLog).where(
                SurveyPromptLog.anonymous_user_hash == anonymous_user_hash,
                col(SurveyPromptLog.user_id).is_(None),
            )
        )
    ).all()
    if anonymous_logs:
        account_logs = {
            log.question_id: log
            for log in (
                await session.exec(
                    select(SurveyPromptLog).where(
                        SurveyPromptLog.user_id == user_id,
                        col(SurveyPromptLog.question_id).in_(
                            [log.question_id for log in anonymous_logs]
                        ),
                    )
                )
            ).all()
        }
        merged_ids = []
        for log in anonymous_logs:
            account_log = account_logs.get(log.question_id)
            if account_log is None:
                log.user_id = user_id
                log.anonymous_user_hash = None
                session.add(log)
                continue
            account_log.shown_count += log.shown_count
            account_log.last_shown_at = max(
                account_log.last_shown_at, log.last_shown_at
            )
            session.add(account_log)
            merged_ids.append(log.id)
        if merged_ids:
            await session.execute(
                sa_delete(SurveyPromptLog).where(
                    col(SurveyPromptLog.id).in_(merged_ids)
                )
            )


async def delete_for_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Part of account erasure: survey answers are demographic data about the
    person, not conversation data kept for research, so they are deleted
    outright rather than stripped of their owner."""
    await session.execute(
        sa_delete(SurveyAnswer).where(SurveyAnswer.user_id == user_id)
    )
    await session.execute(
        sa_delete(SurveyPromptLog).where(SurveyPromptLog.user_id == user_id)
    )


# --- admin -------------------------------------------------------------


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
