import asyncio
from datetime import date

import pytest

from backend.llms import currency
from backend.llms.currency import parse_frankfurter_rate


def test_parse_frankfurter_rate() -> None:
    info = parse_frankfurter_rate(
        {"date": "2026-07-08", "base": "USD", "quote": "DKK", "rate": 6.42},
        "DKK",
    )

    assert info.code == "DKK"
    assert info.rate_from_usd == 6.42
    assert info.date == date(2026, 7, 8)
    assert info.source == "frankfurter"


@pytest.mark.parametrize("rate", [0, True])
def test_rejects_an_invalid_rate(rate: object) -> None:
    with pytest.raises(ValueError, match="invalid rate"):
        parse_frankfurter_rate(
            {"date": "2026-07-08", "base": "USD", "quote": "DKK", "rate": rate},
            "DKK",
        )


def test_rejects_an_unexpected_currency_pair() -> None:
    with pytest.raises(ValueError, match="unexpected currency pair"):
        parse_frankfurter_rate(
            {"date": "2026-07-08", "base": "EUR", "quote": "DKK", "rate": 7.4},
            "DKK",
        )


def test_successful_rate_is_persisted(monkeypatch: pytest.MonkeyPatch) -> None:
    info = currency.CurrencyInfo(
        code="DKK", rate_from_usd=6.42, date=date(2026, 7, 8), source="frankfurter"
    )
    persisted: list[currency.CurrencyInfo] = []

    async def retrieve(_: str) -> currency.CurrencyInfo:
        return info

    async def persist(value: currency.CurrencyInfo) -> None:
        persisted.append(value)

    monkeypatch.setattr(currency.settings, "DISPLAY_CURRENCY", "DKK")
    monkeypatch.setattr(currency.settings, "DISPLAY_CURRENCY_RATE_FROM_USD", None)
    monkeypatch.setattr(currency, "_retrieve_rate", retrieve)
    monkeypatch.setattr(currency, "_persist_rate", persist)
    currency._cache.clear()

    assert asyncio.run(currency.get_currency_info()) == info
    assert persisted == [info]


def test_uses_persisted_rate_when_refresh_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persisted = currency.CurrencyInfo(
        code="DKK", rate_from_usd=6.4, date=date(2026, 7, 7), source="frankfurter"
    )

    async def failing_retrieve(_: str) -> currency.CurrencyInfo:
        raise OSError("Rate service is unavailable")

    async def load(_: str) -> currency.CurrencyInfo:
        return persisted

    monkeypatch.setattr(currency.settings, "DISPLAY_CURRENCY", "DKK")
    monkeypatch.setattr(currency.settings, "DISPLAY_CURRENCY_RATE_FROM_USD", None)
    monkeypatch.setattr(currency, "_retrieve_rate", failing_retrieve)
    monkeypatch.setattr(currency, "_load_persisted_rate", load)
    currency._cache.clear()

    assert asyncio.run(currency.get_currency_info()) == persisted


def test_falls_back_to_usd_when_no_rate_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing_retrieve(_: str) -> currency.CurrencyInfo:
        raise OSError("Rate service is unavailable")

    async def load(_: str) -> None:
        return None

    monkeypatch.setattr(currency.settings, "DISPLAY_CURRENCY", "DKK")
    monkeypatch.setattr(currency.settings, "DISPLAY_CURRENCY_RATE_FROM_USD", None)
    monkeypatch.setattr(currency, "_retrieve_rate", failing_retrieve)
    monkeypatch.setattr(currency, "_load_persisted_rate", load)
    currency._cache.clear()

    assert asyncio.run(currency.get_currency_info()) == currency.CurrencyInfo(
        code="USD", rate_from_usd=1, date=None, source="base"
    )
