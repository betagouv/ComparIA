from datetime import date
from typing import Annotated

from sqlalchemy import Date
from sqlmodel import Field, SQLModel

from .utils import AutoDatetime


class ExchangeRate(SQLModel, table=True):
    """Last successfully retrieved USD exchange rate for one display currency."""

    __tablename__ = "exchange_rate"

    currency_code: str = Field(primary_key=True, max_length=3)
    rate_from_usd: float
    rate_date: Annotated[date, Field(sa_type=Date)]
    updated_at: AutoDatetime
