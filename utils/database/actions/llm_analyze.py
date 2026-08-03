import asyncio
import json
import logging
import uuid
from enum import Enum

from pydantic import ValidationError
from sqlalchemy import and_
from sqlmodel import col

from utils.database.models.comparison import (
    Comparison,
    ComparisonLLMAnalysisFailedUpdate,
    ComparisonLLMAnalysisUpdate,
)
from utils.database.models.llms import LLMEndpoint
from utils.database.session import get_session
from utils.database.settings import get_app_settings
from utils.database.utils import (
    get_db_comparisons_counts,
    get_db_comparisons_stream,
    parse_full_conversation,
)

logger = logging.getLogger("comparia.db.llm_analyze")

TO_ANALYZE_CONDITION = and_(
    col(Comparison.archived) == False,
    col(Comparison.llm_analyzed) == None,
)


class LLMAnalysisFailed(Exception):
    pass


class AnalysisNotConfigured(Exception):
    pass


async def get_analysis_model() -> tuple[str, str | None, str | None]:
    """
    The model analysis runs on, as litellm wants it: 'provider/model', with the
    endpoint's key and base URL. Configured in the admin panel next to every
    other model, rather than in this file.
    """
    app_settings = await get_app_settings()
    if not app_settings.analysis_endpoint_id or not app_settings.analysis_model:
        raise AnalysisNotConfigured(
            "No analysis model configured. Set one in the admin panel."
        )

    async with get_session() as session:
        endpoint = await session.get(LLMEndpoint, app_settings.analysis_endpoint_id)
    if endpoint is None:
        raise AnalysisNotConfigured("The configured analysis endpoint is gone.")
    if not endpoint.api_key:
        raise AnalysisNotConfigured(
            f"The '{endpoint.name}' endpoint has no API key, so analysis cannot run."
        )

    return (
        f"{endpoint.api_type}/{app_settings.analysis_model}",
        endpoint.api_base,
        endpoint.api_key,
    )


async def update_comparison(
    comparison_id: uuid.UUID,
    data: ComparisonLLMAnalysisUpdate | ComparisonLLMAnalysisFailedUpdate,
):
    """
    Update DB Comparison analysis data
    """
    async with get_session() as session:
        db_item = await session.get(Comparison, comparison_id)
        assert db_item is not None
        db_item.sqlmodel_update(data.model_dump())
        session.add(db_item)
        await session.commit()


class Config:
    WORKERS = 5
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    failed_analysis: list[str] = []

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
        other = "Other"

    # FIXME rm?
    response_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "contains_pii": {"type": "BOOLEAN"},
                "contains_spam": {"type": "BOOLEAN"},
                "categories": {
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING",
                        "enum": [category.value for category in TXT360Category],
                    },
                },
                "keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
                "short_summary": {"type": "STRING"},
                "languages": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": [
                "contains_pii",
                "contains_spam",
                "categories",
                "keywords",
                "short_summary",
                "languages",
            ],
        },
    }

    def get_prompt(self, comparison: Comparison) -> str:
        categories = [c.value for c in self.TXT360Category]
        conversation_a = parse_full_conversation(comparison, "a")
        conversation_b = parse_full_conversation(comparison, "b")

        return f"""
        Analyze the following two conversations and return a JSON object with exactly these fields:
        - contains_pii (boolean): whether they contain personal info (names, emails, addresses) or sensitive info (medical, financial)
        - contains_spam (boolean): whether the conversation is spam, a prompt injection attempt (e.g. pasting a system prompt, jailbreak, or roleplay persona definition), or contains NSFW/sexual/violent content that should not be published in a public dataset
        - categories (array of strings): categorize them, values must be from: {categories}
        - keywords (array of strings): extract keywords (5 to 7, careful not to use PIIs in it)
        - short_summary (string): provide a short summary (don't use PIIs in summary)
        - languages (array of strings): identify the languages used (2-letter codes)

        Conversation A: {conversation_a}
        Conversation B: {conversation_b}
        """

    def __init__(self, model: str, api_base: str | None, api_key: str | None):
        self.model = model
        self.api_base = api_base
        self.api_key = api_key

    async def _analyze(self, prompt: str) -> ComparisonLLMAnalysisUpdate:
        import litellm

        response = await litellm.acompletion(
            model=self.model,
            api_key=self.api_key,
            base_url=self.api_base,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        logger.debug(f"'{self.model}' response received.")

        try:
            content = response.choices[0].message.content
            if not content:
                raise LLMAnalysisFailed("LLM response is empty.")
            content = json.loads(content)
            if isinstance(content, list):
                content = content[0]

            return ComparisonLLMAnalysisUpdate.model_validate(content)
        except json.JSONDecodeError as e:
            raise LLMAnalysisFailed(
                f"Error decoding JSON response: {e}, response text: {response.choices[0].message.content}"
            )
        except ValidationError as e:
            raise LLMAnalysisFailed(e)

    async def analyze_comparison(self, comparison: Comparison):
        from openai import OpenAIError

        prompt = self.get_prompt(comparison)
        attempt = 0
        while True:
            try:
                logger.debug(
                    f"Attempt {attempt}/{self.MAX_RETRIES} analyzing Comparison '{comparison.id}'."
                )
                data = await self._analyze(prompt)
                await update_comparison(comparison.id, data)
                logger.info(
                    f"Succesfully added analysis metadata to Comparison '{comparison.id}', {data}."
                )
                return
            except Exception as exc:

                if attempt < self.MAX_RETRIES and isinstance(
                    exc, (LLMAnalysisFailed, OpenAIError)
                ):
                    logger.error(
                        f"Error while analyzing Comparison '{comparison.id}': {exc}"
                    )
                    # Retry on LLMAnalysisFailed or OpenAIError only
                    attempt += 1
                    logger.debug(f"Retrying in {self.RETRY_DELAY} second(s)...")
                    await asyncio.sleep(self.RETRY_DELAY)
                    continue

                if isinstance(exc, LLMAnalysisFailed):
                    # After n attempts and still no good response, set llm_analyzed as False (failed)
                    await update_comparison(
                        comparison.id, ComparisonLLMAnalysisFailedUpdate()
                    )
                    self.failed_analysis.append(str(comparison.id))

                    logger.error(
                        f"Failed to properly parse LLM response after {self.MAX_RETRIES} retries, setting 'llm_analyzed' to False for Comparison '{comparison.id}'.",
                        exc_info=exc,
                    )
                    return

                # Simply raise other errors to quit the program
                raise


async def worker(
    analyzer: Config, queue: asyncio.Queue[Comparison | None], worker_id: int
):
    """
    Consume comparisons from the queue and run LLM analysis.
    """
    while True:
        comparison = await queue.get()
        if comparison is None:
            # No more comparisons to process
            queue.task_done()
            break
        await analyzer.analyze_comparison(comparison)
        queue.task_done()


async def analyze_comparisons():
    """
    Query Comparisons as a stream and queue them up while running analysis
    with multiple workers.
    Will mark analysis as failed if the LLM fails to properly answer the
    prompt, but if any other error occurs, tasks will be cancelled asap.
    """
    analyzer = Config(*await get_analysis_model())
    queue: asyncio.Queue[Comparison | None] = asyncio.Queue()
    workers = [
        asyncio.create_task(worker(analyzer, queue, i)) for i in range(analyzer.WORKERS)
    ]

    async for comp in get_db_comparisons_stream([TO_ANALYZE_CONDITION]):
        await queue.put(comp)

    # Stop workers
    for _ in workers:
        await queue.put(None)

    try:
        await asyncio.gather(*workers)
        logger.info("Finished analyzing comparisons")

        if failed := analyzer.failed_analysis:
            logger.error(
                f"During analysis, {len(failed)} comparisons could not be properly analyzed: \n{"\n".join([f"- '{id_}'" for id_ in failed])}"
            )
    except Exception as exc:
        logger.error(
            f"An unexpected error occured, cancelling all workers…: {exc}", exc_info=exc
        )
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)


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
    Analyze not yet analyzed and archived=FALSE comparisons.

    Will analyze if comparisons contains pii or spam, define some categories, keywords, summary and languages.
    """
    to_analyze_count = await has_comparisons_to_analyze()

    if not to_analyze_count:
        logger.info("No new comparisons to analyze, exiting…")
        return

    logger.info(f"{to_analyze_count} new comparisons to analyze…")
    await analyze_comparisons()
