import asyncio
from datetime import date

from backend.llms import currency
from backend.llms.currency import parse_frankfurter_rate


def test_parse_frankfurter_rate() -> None:
    info = parse_frankfurter_rate(
        {"date": "2026-07-08", "base": "EUR", "quote": "DKK", "rate": 7.4754},
        "DKK",
    )

    assert info.code == "DKK"
    assert info.rate_from_eur == 7.4754
    assert info.date == date(2026, 7, 8)
    assert info.source == "frankfurter"


def test_rejects_an_unexpected_currency_pair() -> None:
    try:
        parse_frankfurter_rate(
            {"date": "2026-07-08", "base": "USD", "quote": "DKK", "rate": 7.4754},
            "DKK",
        )
    except ValueError as error:
        assert "unexpected currency pair" in str(error)
    else:
        raise AssertionError("An unexpected currency pair must be rejected")


def test_rejects_an_invalid_rate() -> None:
    try:
        parse_frankfurter_rate(
            {"date": "2026-07-08", "base": "EUR", "quote": "USD", "rate": 0},
            "USD",
        )
    except ValueError as error:
        assert "invalid rate" in str(error)
    else:
        raise AssertionError("A non-positive exchange rate must be rejected")


def test_rejects_a_boolean_rate() -> None:
    try:
        parse_frankfurter_rate(
            {"date": "2026-07-08", "base": "EUR", "quote": "USD", "rate": True},
            "USD",
        )
    except ValueError as error:
        assert "invalid rate" in str(error)
    else:
        raise AssertionError("A boolean exchange rate must be rejected")


def test_falls_back_to_euros_when_the_first_rate_request_fails() -> None:
    async def failing_retrieve_rate(_: str) -> currency.CurrencyInfo:
        raise OSError("Rate service is unavailable")

    original_currency = currency.settings.DISPLAY_CURRENCY
    original_retrieve_rate = currency._retrieve_rate
    original_cache = currency._cache.copy()
    currency.settings.DISPLAY_CURRENCY = "DKK"
    currency._cache.clear()
    currency._retrieve_rate = failing_retrieve_rate
    try:
        info = asyncio.run(currency.get_currency_info())
    finally:
        currency.settings.DISPLAY_CURRENCY = original_currency
        currency._retrieve_rate = original_retrieve_rate
        currency._cache.clear()
        currency._cache.update(original_cache)

    assert info == currency.CurrencyInfo(
        code="EUR", rate_from_eur=1, date=None, source="base"
    )


if __name__ == "__main__":
    test_parse_frankfurter_rate()
    test_rejects_an_unexpected_currency_pair()
    test_rejects_an_invalid_rate()
    test_rejects_a_boolean_rate()
    test_falls_back_to_euros_when_the_first_rate_request_fails()
