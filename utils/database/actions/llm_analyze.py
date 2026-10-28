"""
The check run on each comparison before the publish run sends it out.

The decision model the prompt check uses reads the whole comparison, the
visitor's messages and both answers, and answers yes/no questions with the
probability of yes: the admin's exclusion criteria (personal data, spam), one
question per topic and one per language. A long comparison is cut into
windows like a prompt, and each question takes its highest score over them.
Every score is kept on the comparison, so `analysis_reapply` can move a
threshold later without asking the model again.

A comparison the model cannot score after MAX_RETRIES tries is marked failed
and stays out of the dataset. A refused key or no credits stops the run.
"""

import asyncio
import logging
import uuid
from enum import Enum
from typing import Final, NamedTuple

import httpx
from sqlalchemy import and_, or_
from sqlmodel import col

from backend.arena.checks import (
    KEY_REJECTED_STATUS,
    NO_CREDITS_STATUS,
    CallLimits,
    ask,
    ask_model,
    chunks,
    highest,
    texts_to_score,
)
from utils.database.dataset_checks import dataset_check_api_key, get_dataset_check
from utils.database.encrypted import UnreadableRow, UnreadableSecret
from utils.database.models.comparison import (
    Comparison,
    ComparisonLLMAnalysisFailedUpdate,
    ComparisonLLMAnalysisUpdate,
)
from utils.database.models.dataset_check import DatasetCheck, DatasetCheckCriterion
from utils.database.models.messages import UserMessageRead
from utils.database.session import get_session
from utils.database.settings import get_app_settings
from utils.database.utils import get_db_comparisons_counts, get_db_comparisons_stream
from utils.secrets import SecretUnreadableError
from utils.storage.redis import REDIS_ANALYSIS_CALLS_KEY

logger = logging.getLogger("comparia.db.llm_analyze")

# The analysis decides what gets published, and partner programme
# conversations (Pix pupils) never are: sending them to the analysis model
# would only pass pupils' text to one more provider.
NO_COHORT = or_(col(Comparison.cohorts).is_(None), col(Comparison.cohorts) == "")

TO_ANALYZE_CONDITION = and_(
    col(Comparison.archived) == False,
    col(Comparison.llm_analyzed) == None,
    NO_COHORT,
)


WORKERS: Final[int] = 2
MAX_RETRIES: Final[int] = 3
RETRY_DELAY: Final[float] = 1.0
# Bounds how far the DB stream can run ahead of the workers: every queued
# Comparison holds its turns and messages in memory.
QUEUE_SIZE: Final[int] = 10
# About 300,000 characters. Past it a comparison is not sent at all and counts
# as failed: no sincere exchange runs that long.
MAX_WINDOWS: Final[int] = 40
# A batch job can wait: its own pool of two calls, so visitors' prompt checks
# keep theirs, a minute per comparison, and as long as Retry-After asks.
LIMITS: Final[CallLimits] = CallLimits(
    slot_key=REDIS_ANALYSIS_CALLS_KEY,
    parallel=2,
    deadline=60.0,
    lease=63.0,
    rate_limit_wait=None,
)

# Read next to every window when the admin left the description empty.
FALLBACK_DESCRIPTION: Final[str] = (
    "An arena where anyone chats with two anonymous AI models. The conversations "
    "kept are published in an open dataset."
)

CATEGORY_PREFIX: Final[str] = "category_"
LANGUAGE_PREFIX: Final[str] = "language_"


class TXT360Category(str, Enum):
    arts = "Arts"
    business_economics_finance = "Business & Economics & Finance"
    culture_cultural_geography = "Culture & Cultural geography"
    daily_life_home_lifestyle = "Daily Life & Home & Lifestyle"
    education = "Education"
    entertainment_travel_hobby = "Entertainment & Travel & Hobby"
    environment = "Environment"
    food_drink_cooking = "Food & Drink & Cooking"
    health_wellness_medicine = "Health & Wellness & Medicine"
    law_justice = "Law & Justice"
    natural_science_formal_science_technology = (
        "Natural Science & Formal Science & Technology"
    )
    personal_development_human_resources_career = (
        "Personal Development & Human Resources & Career"
    )
    politics_government = "Politics & Government"
    religion_spirituality = "Religion & Spirituality"
    shopping_commodity = "Shopping & Commodity"
    society_social_issues_human_rights = "Society & Social Issues & Human Rights"
    sports = "Sports"
    # Not asked: what a comparison gets when no topic reaches the threshold.
    other = "Other"


# Asked on every instance, whatever its locales, since visitors write in any.
COMMON_LANGUAGES: Final[tuple[str, ...]] = (
    "en",
    "fr",
    "es",
    "de",
    "it",
    "pt",
    "ar",
    "zh",
)
LANGUAGE_NAMES: Final[dict[str, str]] = {
    "ar": "Arabic",
    "da": "Danish",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
    "lt": "Lithuanian",
    "nb": "Norwegian",
    "pt": "Portuguese",
    "sv": "Swedish",
    "zh": "Chinese",
}
OTHER_LANGUAGE: Final[str] = "other"


class AnalysisNotConfigured(Exception):
    pass


class AnalysisStopped(Exception):
    """OpenRouter refused the key or is out of credits: every comparison
    would fail the same way, so the run stops instead."""


class Question(NamedTuple):
    key: str
    question: str
    yes: str = ""
    no: str = ""


def language_codes(default_locale: str, enabled_locales: list[str]) -> list[str]:
    """The languages asked about, the instance's first, as the two-letter
    codes the `languages` column holds."""
    codes = [default_locale, *enabled_locales, *COMMON_LANGUAGES]
    return list(dict.fromkeys(code.split("-")[0].lower() for code in codes))


def category_questions() -> list[Question]:
    return [
        Question(
            f"{CATEGORY_PREFIX}{category.name}",
            f"Is {category.value} one of the main topics of the conversation in "
            "the `message`?",
            "The questions asked or the tasks given are about this topic.",
            "The topic is absent or only mentioned in passing.",
        )
        for category in TXT360Category
        if category is not TXT360Category.other
    ]


def language_questions(codes: list[str]) -> list[Question]:
    named = [LANGUAGE_NAMES.get(code, code) for code in codes]
    asked = [
        Question(
            f"{LANGUAGE_PREFIX}{code}",
            f"Is any part of the conversation in the `message` written in {name}?",
            "At least one message or answer is written in this language.",
            "The language only shows up as a quoted word, a name or a title.",
        )
        for code, name in zip(codes, named)
    ]
    asked.append(
        Question(
            f"{LANGUAGE_PREFIX}{OTHER_LANGUAGE}",
            "Is any part of the conversation in the `message` written in a "
            f"language other than {', '.join(named)}?",
            "At least one message or answer is written in another language.",
            "Every message and answer is in one of the languages listed.",
        )
    )
    return asked


def conversation_text(comparison: Comparison) -> str:
    """The comparison as it is published: each visitor message, web search
    results included, then both answers, reasoning included."""
    parts = []
    for side in ("a", "b"):
        if system := getattr(comparison, f"system_msg_{side}"):
            parts.append(f"[system {side}]: {system}")
    for turn in comparison.turns:
        # The read model, not the table one: only it merges the results, and
        # reads them back from the dicts the database returns.
        user = UserMessageRead.model_validate(turn.user_msg, from_attributes=True)
        content = user.model_dump(
            include={"content"}, context={"merge_web_search": True}
        )["content"]
        parts.append(f"[user]: {content}")
        for side in ("a", "b"):
            message = getattr(turn, f"llm_msg_{side}")
            if not message:
                continue
            if message.reasoning_content:
                parts.append(f"[model {side}, reasoning]: {message.reasoning_content}")
            if message.content:
                parts.append(f"[model {side}]: {message.content}")
    return "\n\n".join(parts)


class Analysis(NamedTuple):
    model: str
    description: str
    criteria: list[DatasetCheckCriterion]
    category_threshold: float
    language_threshold: float
    languages: list[str]
    api_key: str

    @property
    def exclusion(self) -> dict[str, dict]:
        return ask(self.criteria)

    @property
    def everything(self) -> dict[str, dict]:
        return {
            **self.exclusion,
            **ask(category_questions()),
            **ask(language_questions(self.languages)),
        }


class TooLong(Exception):
    pass


async def score_comparison(
    text: str, analysis: Analysis, limits: CallLimits = LIMITS
) -> dict[str, float]:
    """Highest score per question over every window of the comparison.

    Topics and languages read the text as written. The exclusion criteria also
    read the folded and decoded spellings, as the prompt check does: folding
    rewrites letters, which would only mislead the language questions. Both
    share `limits.deadline`.
    """
    original = chunks(text)
    if len(original) > MAX_WINDOWS:
        raise TooLong(f"{len(original)} windows, over {MAX_WINDOWS}")
    extra = [w for w in texts_to_score(text) if w not in set(original)]
    if len(extra) > 2 * MAX_WINDOWS:
        raise TooLong(f"{len(extra)} more windows once unfolded")

    everything = analysis.everything
    exclusion = analysis.exclusion
    clock = asyncio.get_running_loop().time
    started = clock()
    full = await ask_model(
        original,
        analysis.model,
        analysis.description,
        everything,
        analysis.api_key,
        limits,
    )
    spelled = (
        await ask_model(
            extra,
            analysis.model,
            analysis.description,
            exclusion,
            analysis.api_key,
            limits._replace(deadline=max(limits.deadline - (clock() - started), 0)),
        )
        if extra and exclusion
        else []
    )
    return highest([*full, *spelled])


def update_from_scores(
    scores: dict[str, float],
    model: str,
    criteria: list[DatasetCheckCriterion],
    category_threshold: float,
    language_threshold: float,
) -> ComparisonLLMAnalysisUpdate:
    """Scores and the thresholds in force to what a comparison stores. Writes
    nothing, so the dry runs and `analysis_reapply` give the same answer.

    A question with no score never reaches its threshold, even at 0: a
    criterion added since the row was scored waits for the model."""

    def reaches(key: str, threshold: float) -> bool:
        return key in scores and scores[key] >= threshold

    reached = {c.reason for c in criteria if reaches(c.key, c.threshold)}
    categories = [
        category.value
        for category in TXT360Category
        if category is not TXT360Category.other
        and reaches(f"{CATEGORY_PREFIX}{category.name}", category_threshold)
    ]
    languages = [
        key.removeprefix(LANGUAGE_PREFIX)
        for key, score in scores.items()
        if key.startswith(LANGUAGE_PREFIX) and score >= language_threshold
    ]
    return ComparisonLLMAnalysisUpdate(
        contains_pii="pii" in reached,
        contains_spam="spam" in reached,
        categories=categories or [TXT360Category.other.value],
        languages=languages,
        analysis_scores={"model": model, "scores": scores},
    )


async def get_analysis() -> Analysis:
    """The configuration a run scores with, or AnalysisNotConfigured."""
    check = await get_dataset_check()
    if not check.model:
        raise AnalysisNotConfigured(
            "No decision model set for the dataset check. Pick one on the "
            "publication page."
        )
    api_key = await dataset_check_api_key(check)
    if isinstance(api_key, UnreadableSecret):
        raise SecretUnreadableError(
            UnreadableRow(DatasetCheck.__tablename__, 1, "api_key").message()
        )
    if not api_key:
        raise AnalysisNotConfigured(
            "No OpenRouter key for the dataset check: none on the publication "
            "page, on the prompt check or in OPENROUTER_API_KEY."
        )
    app_settings = await get_app_settings()
    return analysis_for(
        check, api_key, app_settings.default_locale, app_settings.enabled_locales
    )


def analysis_for(
    check: DatasetCheck,
    api_key: str,
    default_locale: str,
    enabled_locales: list[str],
) -> Analysis:
    return Analysis(
        model=check.model,
        description=check.description or FALLBACK_DESCRIPTION,
        criteria=check.typed_criteria,
        category_threshold=check.category_threshold,
        language_threshold=check.language_threshold,
        languages=language_codes(default_locale, enabled_locales),
        api_key=api_key,
    )


async def update_comparison(
    comparison_id: uuid.UUID,
    data: ComparisonLLMAnalysisUpdate | ComparisonLLMAnalysisFailedUpdate,
):
    async with get_session() as session:
        db_item = await session.get(Comparison, comparison_id)
        assert db_item is not None
        db_item.sqlmodel_update(data.model_dump())
        session.add(db_item)
        await session.commit()


def stopping_status(exc: Exception) -> int | None:
    """The HTTP status of a refused key or of no credits, if `exc` is one."""
    if not isinstance(exc, httpx.HTTPStatusError):
        return None
    code = exc.response.status_code
    return code if code in KEY_REJECTED_STATUS or code == NO_CREDITS_STATUS else None


class Analyzer:
    def __init__(self, analysis: Analysis):
        self.analysis = analysis
        self.failed: list[str] = []
        self.analyzed = 0

    async def analyze_comparison(self, comparison: Comparison) -> None:
        text = conversation_text(comparison)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                scores = await score_comparison(text, self.analysis)
                break
            except Exception as exc:
                if status := stopping_status(exc):
                    raise AnalysisStopped(
                        f"OpenRouter answered {status}: the key is refused or out "
                        "of credits. Fix it and run again."
                    ) from exc
                if isinstance(exc, TooLong) or attempt == MAX_RETRIES:
                    await self._fail(comparison, exc)
                    return
                logger.warning(
                    f"Attempt {attempt}/{MAX_RETRIES} failed for Comparison "
                    f"'{comparison.id}': {exc!r}"
                )
                await asyncio.sleep(RETRY_DELAY)

        data = update_from_scores(
            scores,
            self.analysis.model,
            self.analysis.criteria,
            self.analysis.category_threshold,
            self.analysis.language_threshold,
        )
        await update_comparison(comparison.id, data)
        self.analyzed += 1
        logger.info(
            f"Analyzed Comparison '{comparison.id}': pii={data.contains_pii} "
            f"spam={data.contains_spam} categories={data.categories} "
            f"languages={data.languages}"
        )

    async def _fail(self, comparison: Comparison, exc: Exception) -> None:
        # Kept out of the dataset: llm_analyzed False is never published.
        await update_comparison(comparison.id, ComparisonLLMAnalysisFailedUpdate())
        self.failed.append(str(comparison.id))
        logger.error(
            f"Could not analyze Comparison '{comparison.id}', setting "
            f"'llm_analyzed' to False: {exc!r}"
        )


async def worker(analyzer: Analyzer, queue: asyncio.Queue[Comparison | None]):
    while True:
        comparison = await queue.get()
        try:
            if comparison is None:
                break
            await analyzer.analyze_comparison(comparison)
        finally:
            queue.task_done()


async def analyze_comparisons() -> Analyzer:
    """
    Stream the comparisons to analyze to a few workers. A comparison that
    cannot be scored is marked failed and the run goes on; any other error,
    a refused key included, cancels every worker and is raised.
    """
    analyzer = Analyzer(await get_analysis())
    queue: asyncio.Queue[Comparison | None] = asyncio.Queue(maxsize=QUEUE_SIZE)
    workers = [asyncio.create_task(worker(analyzer, queue)) for _ in range(WORKERS)]

    async def produce():
        async for comp in get_db_comparisons_stream([TO_ANALYZE_CONDITION]):
            await queue.put(comp)
        for _ in workers:
            await queue.put(None)

    tasks = [asyncio.create_task(produce()), *workers]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            if exc := task.exception():
                raise exc
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    logger.info(f"Finished analyzing comparisons: {analyzer.analyzed} analyzed")
    if analyzer.failed:
        logger.error(
            f"{len(analyzer.failed)} comparisons could not be analyzed:\n"
            + "\n".join(f"- '{id_}'" for id_ in analyzer.failed)
        )
    return analyzer


async def has_comparisons_to_analyze() -> int:
    counts = await get_db_comparisons_counts(
        {
            "failed_analysis": col(Comparison.llm_analyzed) == False,
            "not_linted": col(Comparison.archived) == None,
            "not_analyzed": TO_ANALYZE_CONDITION,
        }
    )

    logger.info(f"Comparisons not yet linted: {counts["not_linted"]}")
    logger.info(f"Comparisons not yet analyzed: {counts["not_analyzed"]}")
    logger.info(f"Comparisons with failed analysis: {counts["failed_analysis"]}")

    return counts["not_analyzed"]


async def llm_analyze():
    """
    Analyze the comparisons not analyzed yet with the dataset check's decision
    model: personal data, spam, topics and languages.
    """
    to_analyze_count = await has_comparisons_to_analyze()

    if not to_analyze_count:
        logger.info("No new comparisons to analyze, exiting…")
        return

    logger.info(f"{to_analyze_count} new comparisons to analyze…")
    await analyze_comparisons()
