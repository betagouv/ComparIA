import logging
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_validator
from sqlmodel import select

from backend.config import CustomModelsSelection
from backend.errors import UnavailableLLMsSelectionError
from backend.llms.currency import CurrencyInfo, get_currency_info
from backend.llms.models import APILLMData, LLMDataArchived, LLMDataEnabled
from backend.llms.selection import (
    ModeRules,
    draw_pair,
    needs_ranking,
)
from backend.utils.countries import get_ranking
from utils.database.encrypted import UnreadableRow, UnreadableSecret
from utils.database.models.llms import LLMData
from utils.database.models.selection_mode import SelectionModeRules
from utils.database.session import get_session
from utils.database.settings import get_app_settings
from utils.ranking.compute import RankingResult
from utils.storage.redis import REDIS_LLMS_DATA_CACHE_KEY, redis_cache

logger = logging.getLogger("languia")


class LLMsData(BaseModel):
    all: dict[
        UUID,
        Annotated[LLMDataEnabled | LLMDataArchived, Field(discriminator="status")],
    ]

    @field_validator("all", mode="before")
    @classmethod
    def filter_disabled(cls, llms: Any) -> dict[str, Any]:
        """
        Filter out disabled LLMs: the ones without an endpoint, without a key,
        and the ones whose key no configured encryption key opens. The last
        case is an operator's mistake and is logged as such, once per
        endpoint; the rest of the arena keeps running without those models.
        """
        kept: dict[str, Any] = {}
        unreadable: set[Any] = set()
        for llm in llms:
            if llm.status == "archived":
                kept[llm.id] = llm
                continue
            if llm.status != "enabled" or llm.endpoint is None:
                continue
            api_key = llm.endpoint.api_key
            if api_key is None:
                continue
            if isinstance(api_key, UnreadableSecret):
                if llm.endpoint.id not in unreadable:
                    unreadable.add(llm.endpoint.id)
                    ref = UnreadableRow("llm_endpoint", llm.endpoint.id, "api_key")
                    logger.error(
                        f"[SECRETS] {ref.message()}: the models of "
                        f"'{llm.endpoint.name}' are disabled"
                    )
                continue
            kept[llm.id] = llm
        return kept

    @computed_field  # type: ignore[prop-decorator]
    @property
    def enabled(self) -> dict[UUID, LLMDataEnabled]:
        """
        Filter to only enabled models (removes disabled or deprecated models)
        """
        return {
            model.id: model
            for model in self.all.values()
            if isinstance(model, LLMDataEnabled)
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pricey_models(self) -> list[UUID]:
        """
        Commercial models with higher API costs (e.g., Claude, GPT-4)
        These have stricter rate limits applied
        """
        return [model.id for model in self.enabled.values() if model.rate_limited]

    def pick_two(
        self,
        mode: "ModeRules | None" = None,
        custom_selection: CustomModelsSelection = None,
        unavailable_models: list[UUID] = [],
        ranking: RankingResult | None = None,
    ) -> tuple[UUID, UUID]:
        """
        Two models drawn under a selection mode's rules, in random order.
        Without a mode, two models from the whole catalogue.

        Raises UnavailableLLMsSelectionError when the visitor picked a model
        the mode does not let them pick, and NoValidPairError when the mode
        has no valid pair.
        """
        # `AddFirstTextBody` already refuses anything but one or two UUIDs,
        # but nothing has checked a selection that comes from elsewhere.
        selection = custom_selection or ()
        if len(selection) > 2:
            raise ValueError("At most two models can be selected.")
        try:
            picked = [UUID(str(llm_id)) for llm_id in selection]
        except ValueError:
            raise ValueError("Custom LLMs selection contains invalid ids")

        rules: ModeRules = mode or SelectionModeRules()
        if ranking is None and needs_ranking(rules):
            ranking = get_ranking()
        try:
            return draw_pair(rules, self, picked, unavailable_models, ranking)
        except UnavailableLLMsSelectionError:
            logger.warning(f"`custom_models_selection` refused: {picked}")
            raise


@redis_cache(REDIS_LLMS_DATA_CACHE_KEY)
async def get_llms_data() -> LLMsData:
    """
    Load LLMs definitions from database.
    File contains metadata: params, pricing, reasoning capability, licenses, etc.
    """

    try:
        async with get_session() as session:
            llms = (await session.exec(select(LLMData))).all()
            return LLMsData.model_validate({"all": llms})
    except Exception as e:
        logger.error(f"[DB] Error loading LLMsData: {e}")
        raise


class LLMList(BaseModel):
    data_timestamp: float | None
    models: list[APILLMData]
    style_coefficients: dict[str, float] | None
    # How far a model's rank may move either way and still be shown, see
    # AppSettings.ranking_max_rank_spread.
    max_rank_spread: int
    currency: CurrencyInfo


# FIXME use cache?
async def get_llms_list() -> LLMList:
    llms = await get_llms_data()
    ranking = get_ranking()
    currency = await get_currency_info()
    app_settings = await get_app_settings()

    return LLMList.model_validate(
        {
            "models": llms.all.values(),
            "data_timestamp": ranking.timestamp if ranking else None,
            "style_coefficients": ranking.style_coefficients if ranking else None,
            "max_rank_spread": app_settings.ranking_max_rank_spread,
            "currency": currency,
        },
        context={"ranking": ranking},
    )
