"""AuraStream Binance Funding Rates Model."""

from datetime import date as dateType, datetime
from typing import Any

from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.bls_series import SeriesQueryParams
from pydantic import Field

from openbb_aurastream.utils.client import (
    api_key,
    default_start,
    fetch,
    split_symbols,
    to_rows,
)


class AuraStreamFundingRatesQueryParams(SeriesQueryParams):
    """AuraStream Binance Funding Rates Query.

    Source: https://aurastream.unbiased-alpha.com/docs/data-sources/binance/
    """

    __json_schema_extra__ = {"symbol": {"multiple_items_allowed": True}}

    symbol: str = Field(
        default="BTCUSDT",
        description="Binance USD-M perpetual symbol, e.g. 'BTCUSDT', 'ETHUSDT'.",
    )
    start_date: dateType | None = Field(
        default=None, description="Start date. Default: one year ago."
    )
    end_date: dateType | None = Field(
        default=None, description="End date. Default: today."
    )


class AuraStreamFundingRatesData(Data):
    """AuraStream Binance Funding Rates Data. One row per funding time."""

    __alias_dict__ = {"funding_rate": "fundingRate"}

    date: datetime = Field(description="Funding time.")
    symbol: str = Field(description="Perpetual symbol.")
    funding_rate: float | None = Field(
        default=None,
        description="Funding rate for the period, as a fraction (0.0001 = 0.01%).",
    )


class AuraStreamFundingRatesFetcher(
    Fetcher[AuraStreamFundingRatesQueryParams, list[AuraStreamFundingRatesData]]
):
    """Fetch Binance perpetual funding rates from AuraStream."""

    require_credentials = False

    @staticmethod
    def transform_query(params: dict[str, Any]) -> AuraStreamFundingRatesQueryParams:
        """Transform the query."""
        return AuraStreamFundingRatesQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: AuraStreamFundingRatesQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Return the raw rows."""
        symbols = [s.upper() for s in split_symbols(query.symbol)]
        body = {
            "tickerlist": symbols,
            "start": str(query.start_date or default_start()),
            "end": str(query.end_date or dateType.today()),
            "interval": "1h",
            "source": "binance",
            "instrument": "futures",
            "bars": "funding",
        }
        data = await fetch(body, api_key(credentials))
        return to_rows(data, symbols)

    @staticmethod
    def transform_data(
        query: AuraStreamFundingRatesQueryParams, data: list[dict], **kwargs: Any
    ) -> list[AuraStreamFundingRatesData]:
        """Transform the data."""
        return [AuraStreamFundingRatesData.model_validate(d) for d in data]
