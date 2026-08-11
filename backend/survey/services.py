import re
import unicodedata
import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.database.models.survey import (
    MAX_QUESTION_PROMPTS,
    MAX_QUESTIONS_PER_PROMPT,
    AdminSurveyCombination,
    AdminSurveyOption,
    AdminSurveyQuestion,
    AdminSurveyResponse,
    MySurveyAnswer,
    PublicSurveyOption,
    PublicSurveyQuestion,
    SurveyAnswer,
    SurveyAnswerSubmit,
    SurveyInputType,
    SurveyOption,
    SurveyOptionWrite,
    SurveyPromptLog,
    SurveyQuestion,
    SurveyQuestionCreate,
    SurveyQuestionOrder,
    SurveyQuestionUpdate,
    SurveyTrigger,
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


class SurveyOptionUnknownError(Exception):
    """
    A key that is not a live option on the question (submitting an answer), or
    not one of the question's existing options at all (editing one).
    """


class SurveyOrderMismatchError(Exception):
    """An order has to list every question on the trigger, and nothing else."""


# --- shared helpers -------------------------------------------------------


def _key(label: str) -> str:
    """
    Derive a stable, ascii, column-safe key from a label. Copied from
    `backend/vote_tags/services.py::_tag_key` in spirit: question keys and
    option keys both work the same way.
    """
    normalized = (
        unicodedata.normalize("NFKD", label)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")[:100]


async def _label(labels: dict[str, str], locale: str) -> str:
    """Exact locale, then the instance default, then whatever is there."""
    if locale in labels:
        return labels[locale]
    default_locale = (await get_app_settings()).default_locale
    return labels.get(default_locale) or next(iter(labels.values()))


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


def _respondent_of(row) -> tuple[str, object]:
    return ("user", row.user_id) if row.user_id else ("anon", row.anonymous_user_hash)


def _check_answer_shape(input_type: SurveyInputType, option_keys: list[str]) -> None:
    """A 'select' question is single-choice: the frontend renders radios, and a
    second key arriving anyway means the client and the question disagree
    about its own shape."""
    if input_type == "select" and len(option_keys) > 1:
        raise ValueError("a 'select' question accepts at most one option")


@redis_cache(REDIS_SURVEY_KEY)
async def _all_questions() -> list[SurveyQuestion]:
    """
    Every question, archived ones included, in display order within each
    trigger. Cached the way `vote_tags` caches its full tag list: question
    wording changes rarely, so one cached list serves every locale and every
    respondent.
    """
    async with get_session() as session:
        result = await session.exec(
            select(SurveyQuestion).order_by(
                col(SurveyQuestion.trigger), col(SurveyQuestion.display_order)
            )
        )
        return list(result.all())


async def _to_public(
    question: SurveyQuestion, locale: str, *, include_archived: bool = False
) -> PublicSurveyQuestion:
    options = []
    for raw in question.options:
        option = SurveyOption.model_validate(raw)
        if option.archived and not include_archived:
            continue
        options.append(
            PublicSurveyOption(
                key=option.key, label=await _label(option.labels, locale)
            )
        )
    return PublicSurveyQuestion(
        id=question.id,
        key=question.key,
        trigger=question.trigger,
        input_type=question.input_type,
        label=await _label(question.labels, locale),
        revision=question.revision,
        options=options,
    )


# --- public ----------------------------------------------------------------


async def list_questions(
    session: AsyncSession, trigger: SurveyTrigger, locale: str
) -> list[PublicSurveyQuestion]:
    """
    Every live question for a trigger, unconditional on who is asking.
    `signup` questions are all required and use this: there is no respondent
    yet to check answered/shown state against.
    """
    questions = sorted(
        (
            question
            for question in await _all_questions()
            if question.trigger == trigger and question.archived_at is None
        ),
        key=lambda question: question.display_order,
    )
    return [await _to_public(question, locale) for question in questions]


async def questions_to_prompt(
    session: AsyncSession,
    trigger: SurveyTrigger,
    locale: str,
    user_id: uuid.UUID | None,
    anonymous_user_hash: str | None,
) -> list[PublicSurveyQuestion]:
    """
    What the after-vote popup should actually show this respondent: live
    questions they have not answered, not over-shown, not shown too recently.
    """
    _require_respondent(user_id, anonymous_user_hash)

    candidates = sorted(
        (
            question
            for question in await _all_questions()
            if question.trigger == trigger and question.archived_at is None
        ),
        key=lambda question: question.display_order,
    )
    if not candidates:
        return []

    question_ids = [question.id for question in candidates]

    answered_ids = set(
        (
            await session.exec(
                select(SurveyAnswer.question_id)
                .where(col(SurveyAnswer.question_id).in_(question_ids))
                .where(_respondent_clause(SurveyAnswer, user_id, anonymous_user_hash))
                .distinct()
            )
        ).all()
    )

    logs = {
        log.question_id: log
        for log in (
            await session.exec(
                select(SurveyPromptLog)
                .where(col(SurveyPromptLog.question_id).in_(question_ids))
                .where(
                    _respondent_clause(SurveyPromptLog, user_id, anonymous_user_hash)
                )
            )
        ).all()
    }

    reask_after_days = (await get_app_settings()).survey_reask_after_days
    cutoff = utc_now() - timedelta(days=reask_after_days)

    eligible = []
    for question in candidates:
        if question.id in answered_ids:
            continue
        log = logs.get(question.id)
        if log is not None:
            if log.shown_count >= MAX_QUESTION_PROMPTS:
                continue
            if log.last_shown_at is not None and log.last_shown_at > cutoff:
                continue
        eligible.append(question)
        if len(eligible) >= MAX_QUESTIONS_PER_PROMPT:
            break

    return [await _to_public(question, locale) for question in eligible]


async def record_shown(
    session: AsyncSession,
    question_ids: list[uuid.UUID],
    user_id: uuid.UUID | None,
    anonymous_user_hash: str | None,
) -> None:
    """
    Upsert the prompt log for every question just shown. Called both when the
    popup actually renders, and by `POST /survey/dismiss`: closing the popup
    and declining it are deliberately the same thing.
    """
    _require_respondent(user_id, anonymous_user_hash)
    if not question_ids:
        return

    existing = {
        log.question_id: log
        for log in (
            await session.exec(
                select(SurveyPromptLog)
                .where(col(SurveyPromptLog.question_id).in_(question_ids))
                .where(
                    _respondent_clause(SurveyPromptLog, user_id, anonymous_user_hash)
                )
            )
        ).all()
    }

    now = utc_now()
    for question_id in question_ids:
        log = existing.get(question_id)
        if log is None:
            log = SurveyPromptLog(
                question_id=question_id,
                user_id=user_id,
                anonymous_user_hash=anonymous_user_hash,
                shown_count=1,
                last_shown_at=now,
            )
        else:
            log.shown_count += 1
            log.last_shown_at = now
        session.add(log)


async def submit_answers(
    session: AsyncSession,
    payload: SurveyAnswerSubmit,
    user_id: uuid.UUID | None,
    anonymous_user_hash: str | None,
    terms_version: str | None,
) -> None:
    """
    Replace semantics: each question's answer fully replaces whatever this
    respondent answered before, including clearing it with an empty list.
    """
    _require_respondent(user_id, anonymous_user_hash)

    now = utc_now()
    for answer in payload.answers:
        question = await session.get(SurveyQuestion, answer.question_id)
        if question is None or question.archived_at is not None:
            raise SurveyQuestionNotFoundError()

        _check_answer_shape(question.input_type, answer.option_keys)

        live_keys = {
            option.key
            for option in (SurveyOption.model_validate(raw) for raw in question.options)
            if not option.archived
        }
        unknown = set(answer.option_keys) - live_keys
        if unknown:
            raise SurveyOptionUnknownError(", ".join(sorted(unknown)))

        await session.execute(
            sa_delete(SurveyAnswer)
            .where(SurveyAnswer.question_id == answer.question_id)
            .where(_respondent_clause(SurveyAnswer, user_id, anonymous_user_hash))
        )

        for option_key in answer.option_keys:
            session.add(
                SurveyAnswer(
                    question_id=answer.question_id,
                    option_key=option_key,
                    user_id=user_id,
                    anonymous_user_hash=anonymous_user_hash,
                    question_revision=question.revision,
                    terms_version=terms_version,
                    answered_at=now,
                )
            )


async def my_answers(
    session: AsyncSession,
    locale: str,
    user_id: uuid.UUID | None,
    anonymous_user_hash: str | None,
) -> list[MySurveyAnswer]:
    """What the profile page and the personal-data export show: every question
    this respondent has answered, options included so an option archived since
    the answer was given still resolves to a label."""
    _require_respondent(user_id, anonymous_user_hash)

    rows = (
        await session.exec(
            select(SurveyAnswer).where(
                _respondent_clause(SurveyAnswer, user_id, anonymous_user_hash)
            )
        )
    ).all()
    if not rows:
        return []

    selected: dict[uuid.UUID, list[str]] = {}
    for row in rows:
        selected.setdefault(row.question_id, []).append(row.option_key)

    questions_by_id = {question.id: question for question in await _all_questions()}

    results = []
    for question_id, option_keys in selected.items():
        question = questions_by_id.get(question_id)
        if question is None:
            continue
        public = await _to_public(question, locale, include_archived=True)
        results.append(
            MySurveyAnswer(
                question_id=question.id,
                question_key=question.key,
                label=public.label,
                input_type=question.input_type,
                options=public.options,
                selected_keys=option_keys,
            )
        )
    return results


async def signup_questions_answered(
    user_id: uuid.UUID | None,
    anonymous_user_hash: str | None,
) -> bool:
    """
    Whether every live signup question has an answer from this respondent.

    Opens its own session, like `has_current_terms_acceptance`: both are
    preconditions the auth routes check before doing any work, and both are
    free on the common path where nothing is configured.
    """
    signup_ids = [
        question.id
        for question in await _all_questions()
        if question.trigger == "signup" and question.archived_at is None
    ]
    # The overwhelmingly common case is an instance with no signup questions
    # at all, and it costs nothing: the question list is cached, so the gate
    # never reaches the database. Checked before the respondent, so an
    # instance with nothing configured answers the same either way.
    if not signup_ids:
        return True

    # A caller with no identity at all cannot have answered anything. Saying
    # so beats raising: this runs on a login route, where an unexpected shape
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
    already_answered = set(
        (
            await session.exec(
                select(SurveyAnswer.question_id).where(SurveyAnswer.user_id == user_id)
            )
        ).all()
    )
    if already_answered:
        # The account's own answer wins over whatever was given anonymously
        # for the same question, so the anonymous duplicate is dropped rather
        # than left to survive alongside it.
        await session.execute(
            sa_delete(SurveyAnswer).where(
                SurveyAnswer.anonymous_user_hash == anonymous_user_hash,
                SurveyAnswer.user_id.is_(None),
                col(SurveyAnswer.question_id).in_(already_answered),
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


async def admin_list(session: AsyncSession) -> AdminSurveyResponse:
    questions = list(
        (
            await session.exec(
                select(SurveyQuestion).order_by(
                    col(SurveyQuestion.trigger), col(SurveyQuestion.display_order)
                )
            )
        ).all()
    )
    all_answers = list((await session.exec(select(SurveyAnswer))).all())

    by_question: dict[uuid.UUID, list[SurveyAnswer]] = {}
    for row in all_answers:
        by_question.setdefault(row.question_id, []).append(row)

    admin_questions = []
    for question in questions:
        rows = by_question.get(question.id, [])
        respondent_count = len({_respondent_of(row) for row in rows})
        answer_counts: dict[str, int] = {}
        for row in rows:
            answer_counts[row.option_key] = answer_counts.get(row.option_key, 0) + 1

        options = [
            AdminSurveyOption(
                key=option.key,
                labels=option.labels,
                archived=option.archived,
                answer_count=answer_counts.get(option.key, 0),
            )
            for option in (SurveyOption.model_validate(raw) for raw in question.options)
        ]

        admin_questions.append(
            AdminSurveyQuestion(
                id=question.id,
                key=question.key,
                trigger=question.trigger,
                input_type=question.input_type,
                labels=question.labels,
                options=options,
                published=question.published,
                revision=question.revision,
                display_order=question.display_order,
                archived=question.archived_at is not None,
                respondent_count=respondent_count,
            )
        )

    total_respondents = len({_respondent_of(row) for row in all_answers})

    # 'combinations': one profile per respondent, built only from published,
    # non-archived questions (unpublished/archived questions never reach the
    # dataset, so they cannot be part of a re-identification risk in it).
    combinable_ids = {
        question.id
        for question in questions
        if question.published and question.archived_at is None
    }
    key_by_question = {question.id: question.key for question in questions}

    profiles: dict[tuple[str, object], dict[str, str]] = {}
    for row in all_answers:
        if row.question_id not in combinable_ids:
            continue
        profile = profiles.setdefault(_respondent_of(row), {})
        question_key = key_by_question[row.question_id]
        if question_key in profile:
            # checkbox_group: fold every selected key into one canonical,
            # order-independent string rather than losing all but the last.
            keys = sorted(profile[question_key].split(",") + [row.option_key])
            profile[question_key] = ",".join(keys)
        else:
            profile[question_key] = row.option_key

    combo_counts: dict[tuple[tuple[str, str], ...], int] = {}
    combo_answers: dict[tuple[tuple[str, str], ...], dict[str, str]] = {}
    for profile in profiles.values():
        combo_key = tuple(sorted(profile.items()))
        combo_counts[combo_key] = combo_counts.get(combo_key, 0) + 1
        combo_answers[combo_key] = profile

    combinations = [
        AdminSurveyCombination(answers=combo_answers[combo_key], count=count)
        for combo_key, count in sorted(combo_counts.items(), key=lambda item: item[1])
    ][:200]

    return AdminSurveyResponse(
        questions=admin_questions,
        combinations=combinations,
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
        await session.exec(
            select(func.max(SurveyQuestion.display_order)).where(
                SurveyQuestion.trigger == payload.trigger
            )
        )
    ).one()

    options = _derive_option_keys(payload.options)

    question = SurveyQuestion(
        key=key,
        trigger=payload.trigger,
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
        # Two labels slugging to the same key is the only way this collides,
        # which is the same complaint as a label with nothing to slug at all.
        raise SurveyQuestionLabelUnusableError() from error

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
    if label_changed or live_set_changed:
        question.revision += 1
    question.updated_at = datetime.now()

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
    # one it owns; updated_at belongs to BaseDBModel, whose default is the
    # host's local time, and matching it keeps a row's own two stamps
    # comparable.
    question.archived_at = utc_now() if archived else None
    question.archived_by = admin_id if archived else None
    question.updated_at = datetime.now()
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
    """Write one trigger's order from the list the client sends. It has to
    name every question on that trigger exactly once, so a stale page cannot
    drop a question another admin added in the meantime."""
    siblings = list(
        (
            await session.exec(
                select(SurveyQuestion).where(SurveyQuestion.trigger == payload.trigger)
            )
        ).all()
    )
    by_id = {row.id: row for row in siblings}
    if len(payload.ids) != len(by_id) or set(payload.ids) != set(by_id):
        raise SurveyOrderMismatchError()

    for position, question_id in enumerate(payload.ids):
        row = by_id[question_id]
        row.display_order = position
        session.add(row)

    await session.commit()
    invalidate_cache(REDIS_SURVEY_KEY)
