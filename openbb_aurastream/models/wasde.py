"""AuraStream USDA WASDE Model."""

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


class AuraStreamWasdeQueryParams(SeriesQueryParams):
    """AuraStream USDA WASDE Query.

    Source: https://aurastream.unbiased-alpha.com/docs/data-sources/wasde/
    """

    __json_schema_extra__ = {"symbol": {"multiple_items_allowed": True}}

    symbol: str = Field(
        description="'commodity:attribute' for the US balance sheet (e.g. 'corn:ending_stocks'),"
        + " or 'commodity:attribute:region' for the world tables (e.g. 'soybeans:production:Brazil').",
    )
    start_date: dateType | None = Field(
        default=None, description="Start date. Default: one year ago."
    )
    end_date: dateType | None = Field(
        default=None, description="End date. Default: today."
    )


    @field_validator("symbol", mode="before", check_fields=False)
    @classmethod
    def to_upper(cls, v: str) -> str:
        """Keep the symbol as written: these tickers are case-sensitive."""
        return v


class AuraStreamWasdeData(Data):
    """AuraStream USDA WASDE Data. One row per report."""

    date: datetime = Field(description="Report release time (12:00 New York).")
    symbol: str = Field(description="The series as requested.")
    report: str | None = Field(
        default=None, description="Report month, e.g. 'October 2026'."
    )
    market_year: str | None = Field(
        default=None, description="Marketing year projected, e.g. '2026/27'."
    )
    value: float | None = Field(default=None, description="This report's projection.")
    previous: float | None = Field(
        default=None,
        description="The previous month's projection, as printed in the same report.",
    )
    prior_year: str | None = Field(default=None, description="The year before.")
    prior_year_value: float | None = Field(
        default=None, description="The estimate for the year before."
    )


class AuraStreamWasdeFetcher(
    Fetcher[AuraStreamWasdeQueryParams, list[AuraStreamWasdeData]]
):
    """Fetch WASDE projections from AuraStream."""

    require_credentials = False

    @staticmethod
    def transform_query(params: dict[str, Any]) -> AuraStreamWasdeQueryParams:
        """Transform the query."""
        return AuraStreamWasdeQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: AuraStreamWasdeQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Return the raw rows."""
        symbols = split_symbols(query.symbol)
        body = {
            "tickerlist": symbols,
            "start": str(query.start_date or default_start()),
            "end": str(query.end_date or dateType.today()),
            "interval": "1m",
            "source": "wasde",
        }
        data = await fetch(body, api_key(credentials))
        return to_rows(data, symbols)

    @staticmethod
    def transform_data(
        query: AuraStreamWasdeQueryParams, data: list[dict], **kwargs: Any
    ) -> list[AuraStreamWasdeData]:
        """Transform the data."""
        return [AuraStreamWasdeData.model_validate(d) for d in data]
