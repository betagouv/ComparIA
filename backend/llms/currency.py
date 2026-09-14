"""Display currency configuration and daily exchange-rate retrieval."""

import asyncio
import logging
import math
from datetime import date
from time import monotonic
from typing import Literal

import httpx
from pydantic import BaseModel
from backend.config import settings
from utils.database.models.exchange_rate import ExchangeRate
from utils.database.session import get_session

logger = logging.getLogger("languia")


class CurrencyInfo(BaseModel):
    code: str
    rate_from_usd: float
    date: date | None
    source: Literal["base", "frankfurter", "manual"]


class _CachedRate(BaseModel):
    info: CurrencyInfo
    expires_at: float


_cache: dict[str, _CachedRate] = {}
_cache_lock = asyncio.Lock()


def parse_frankfurter_rate(payload: object, expected_currency: str) -> CurrencyInfo:
    if not isinstance(payload, dict):
        raise ValueError("Exchange-rate response must be an object")

    base = payload.get("base")
    quote = payload.get("quote")
    rate = payload.get("rate")
    rate_date = payload.get("date")
    if base != "USD" or quote != expected_currency:
        raise ValueError("Exchange-rate response contains an unexpected currency pair")
    if (
        isinstance(rate, bool)
        or not isinstance(rate, int | float)
        or not math.isfinite(rate)
        or rate <= 0
    ):
        raise ValueError("Exchange-rate response contains an invalid rate")
    if not isinstance(rate_date, str):
        raise ValueError("Exchange-rate response contains an invalid date")

    return CurrencyInfo(
        code=expected_currency,
        rate_from_usd=float(rate),
        date=date.fromisoformat(rate_date),
        source="frankfurter",
    )


async def _retrieve_rate(currency: str) -> CurrencyInfo:
    url = f"{settings.EXCHANGE_RATE_API_URL.rstrip('/')}/rate/USD/{currency}"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(url, headers={"Accept": "application/json"})
        response.raise_for_status()
        return parse_frankfurter_rate(response.json(), currency)


async def _load_persisted_rate(currency: str) -> CurrencyInfo | None:
    try:
        async with get_session() as session:
            stored = await session.get(ExchangeRate, currency)
    except Exception:
        logger.warning(
            "[CURRENCY] Could not load the persisted USD/%s rate",
            currency,
            exc_info=True,
        )
        return None
    if stored is None:
        return None
    return CurrencyInfo(
        code=currency,
        rate_from_usd=stored.rate_from_usd,
        date=stored.rate_date,
        source="frankfurter",
    )


async def _persist_rate(info: CurrencyInfo) -> None:
    if info.date is None:
        raise ValueError("Retrieved exchange rates must include their effective date")
    try:
        async with get_session() as session:
            stored = await session.get(ExchangeRate, info.code)
            if stored is None:
                stored = ExchangeRate(
                    currency_code=info.code,
                    rate_from_usd=info.rate_from_usd,
                    rate_date=info.date,
                )
            else:
                stored.rate_from_usd = info.rate_from_usd
                stored.rate_date = info.date
            session.add(stored)
            await session.commit()
    except Exception:
        # A fetched rate is still useful for this process even if durable caching fails.
        logger.warning(
            "[CURRENCY] Could not persist the USD/%s rate", info.code, exc_info=True
        )


async def get_currency_info() -> CurrencyInfo:
    currency = settings.DISPLAY_CURRENCY
    if currency == "USD":
        return CurrencyInfo(code="USD", rate_from_usd=1, date=None, source="base")

    if manual_rate := settings.DISPLAY_CURRENCY_RATE_FROM_USD:
        return CurrencyInfo(
            code=currency,
            rate_from_usd=manual_rate,
            date=None,
            source="manual",
        )

    now = monotonic()
    cached = _cache.get(currency)
    if cached and cached.expires_at > now:
        return cached.info

    async with _cache_lock:
        now = monotonic()
        cached = _cache.get(currency)
        if cached and cached.expires_at > now:
            return cached.info
        try:
            info = await _retrieve_rate(currency)
        except Exception:
            if cached:
                logger.warning(
                    "[CURRENCY] Rate refresh failed for %s; using stale rate from %s",
                    currency,
                    cached.info.date,
                    exc_info=True,
                )
                return cached.info
            persisted = await _load_persisted_rate(currency)
            if persisted is not None:
                logger.warning(
                    "[CURRENCY] Rate refresh failed for %s; using persisted rate from %s",
                    currency,
                    persisted.date,
                    exc_info=True,
                )
                return persisted
            logger.warning(
                "[CURRENCY] Could not retrieve USD/%s rate; falling back to USD",
                currency,
                exc_info=True,
            )
            return CurrencyInfo(code="USD", rate_from_usd=1, date=None, source="base")

        _cache[currency] = _CachedRate(
            info=info,
            expires_at=now + settings.EXCHANGE_RATE_CACHE_SECONDS,
        )
        await _persist_rate(info)
        return info
