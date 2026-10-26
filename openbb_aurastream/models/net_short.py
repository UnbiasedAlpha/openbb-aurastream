"""AuraStream EU Net Short Positions Model."""

from datetime import date as dateType, datetime
from typing import Any

from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.bls_series import SeriesQueryParams
from pydantic import Field, field_validator

from openbb_aurastream.utils.client import (
    api_key,
    default_start,
    fetch,
    split_symbols,
    to_rows,
)


class AuraStreamNetShortQueryParams(SeriesQueryParams):
    """AuraStream EU Net Short Positions Query.

    Source: https://aurastream.unbiased-alpha.com/docs/data-sources/netshort/
    """

    __json_schema_extra__ = {
        "symbol": {"multiple_items_allowed": True},
        "country": {"multiple_items_allowed": True, "choices": ["FR", "NL", "ES"]},
    }

    symbol: str = Field(
        description="ISIN (e.g. 'FR0000054470'), part of the issuer's name (e.g. 'ubisoft'),"
        + " or 'all' for every position in the period.",
    )
    start_date: dateType | None = Field(
        default=None, description="Start date. Default: one year ago."
    )
    end_date: dateType | None = Field(
        default=None, description="End date. Default: today."
    )
    country: str | None = Field(
        default=None,
        description="Registers to search: FR (AMF), NL (AFM), ES (CNMV). Default: all three.",
    )
    holder: str | None = Field(
        default=None,
        description="Keep positions whose holder name contains this text, e.g. 'citadel'.",
    )


    @field_validator("symbol", mode="before", check_fields=False)
    @classmethod
    def to_upper(cls, v: str) -> str:
        """Keep the symbol as written: these tickers are case-sensitive."""
        return v


class AuraStreamNetShortData(Data):
    """AuraStream EU Net Short Positions Data. One row per published position."""

    date: datetime = Field(description="Position date.")
    symbol: str = Field(description="The symbol as requested.")
    holder: str | None = Field(default=None, description="Position holder.")
    issuer: str | None = Field(default=None, description="Company name.")
    isin: str | None = Field(default=None, description="Company ISIN.")
    net_short_pct: float | None = Field(
        default=None,
        description="Net short position, in percent of issued share capital (0.62 = 0.62%).",
    )
    country: str | None = Field(default=None, description="FR, NL or ES.")
    holder_lei: str | None = Field(
        default=None, description="Holder's Legal Entity Identifier (France only)."
    )
    published_from: str | None = Field(
        default=None, description="First date on the public register (France only)."
    )
    published_to: str | None = Field(
        default=None, description="Last date on the public register (France only)."
    )
    source: str | None = Field(
        default=None, description="The attribution the regulator requires."
    )


class AuraStreamNetShortFetcher(
    Fetcher[AuraStreamNetShortQueryParams, list[AuraStreamNetShortData]]
):
    """Fetch EU net short positions from AuraStream."""

    require_credentials = False

    @staticmethod
    def transform_query(params: dict[str, Any]) -> AuraStreamNetShortQueryParams:
        """Transform the query."""
        return AuraStreamNetShortQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: AuraStreamNetShortQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Return the raw rows."""
        symbols = split_symbols(query.symbol)
        body: dict[str, Any] = {
            "tickerlist": symbols,
            "start": str(query.start_date or default_start()),
            "end": str(query.end_date or dateType.today()),
            "interval": "1d",
            "source": "netshort",
        }
        if query.country:
            body["country"] = [c.upper() for c in split_symbols(query.country)]
        if query.holder:
            body["holder"] = query.holder
        data = await fetch(body, api_key(credentials))
        return to_rows(data, symbols)

    @staticmethod
    def transform_data(
        query: AuraStreamNetShortQueryParams, data: list[dict], **kwargs: Any
    ) -> list[AuraStreamNetShortData]:
        """Transform the data."""
        return [AuraStreamNetShortData.model_validate(d) for d in data]
