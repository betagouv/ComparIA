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

logger = logging.getLogger("languia")


class CurrencyInfo(BaseModel):
    code: str
    rate_from_eur: float
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
    if base != "EUR" or quote != expected_currency:
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
        rate_from_eur=float(rate),
        date=date.fromisoformat(rate_date),
        source="frankfurter",
    )


async def _retrieve_rate(currency: str) -> CurrencyInfo:
    url = f"{settings.EXCHANGE_RATE_API_URL.rstrip('/')}/rate/EUR/{currency}"
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(url, headers={"Accept": "application/json"})
        response.raise_for_status()
        return parse_frankfurter_rate(response.json(), currency)


async def get_currency_info() -> CurrencyInfo:
    currency = settings.DISPLAY_CURRENCY
    if currency == "EUR":
        return CurrencyInfo(code="EUR", rate_from_eur=1, date=None, source="base")

    if manual_rate := settings.DISPLAY_CURRENCY_RATE_FROM_EUR:
        return CurrencyInfo(
            code=currency,
            rate_from_eur=manual_rate,
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
            logger.warning(
                "[CURRENCY] Could not retrieve EUR/%s rate; falling back to EUR",
                currency,
                exc_info=True,
            )
            return CurrencyInfo(code="EUR", rate_from_eur=1, date=None, source="base")

        _cache[currency] = _CachedRate(
            info=info,
            expires_at=now + settings.EXCHANGE_RATE_CACHE_SECONDS,
        )
        return info
