"""AuraStream Fails-to-Deliver Model."""

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
    require_key,
    split_symbols,
    to_rows,
)


class AuraStreamFailsToDeliverQueryParams(SeriesQueryParams):
    """AuraStream Fails-to-Deliver Query.

    Source: https://aurastream.unbiased-alpha.com/docs/data-sources/edgar/
    """

    __json_schema_extra__ = {"symbol": {"multiple_items_allowed": True}}

    symbol: str = Field(
        description="US stock or ETF symbol (e.g. 'GME') or 9-character CUSIP."
    )
    start_date: dateType | None = Field(
        default=None, description="Start date. Default: one year ago."
    )
    end_date: dateType | None = Field(
        default=None, description="End date. Default: today."
    )


class AuraStreamFailsToDeliverData(Data):
    """AuraStream Fails-to-Deliver Data. One row per settlement date with fails outstanding."""

    date: datetime = Field(description="Settlement date.")
    symbol: str = Field(description="Security symbol.")
    fails: int | None = Field(
        default=None, description="Total fails-to-deliver balance, in shares."
    )
    price: float | None = Field(
        default=None, description="Previous day's closing price."
    )
    cusip: str | None = Field(default=None, description="CUSIP of the security.")
    description: str | None = Field(default=None, description="Security description.")


class AuraStreamFailsToDeliverFetcher(
    Fetcher[AuraStreamFailsToDeliverQueryParams, list[AuraStreamFailsToDeliverData]]
):
    """Fetch SEC fails-to-deliver from AuraStream."""

    require_credentials = False

    @staticmethod
    def transform_query(params: dict[str, Any]) -> AuraStreamFailsToDeliverQueryParams:
        """Transform the query."""
        return AuraStreamFailsToDeliverQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: AuraStreamFailsToDeliverQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Return the raw rows."""
        key = api_key(credentials)
        user_agent = require_key(
            credentials,
            "aurastream_sec_user_agent",
            "The SEC asks every automated request to name the sender: your name or company"
            " and a contact email, e.g. 'Jane Doe jane@example.com'.",
        )
        symbols = [s.upper() for s in split_symbols(query.symbol)]
        body = {
            "tickerlist": symbols,
            "start": str(query.start_date or default_start()),
            "end": str(query.end_date or dateType.today()),
            "interval": "1d",
            "source": "edgar",
            "dataset": "ftd",
            "credentials": {"user_agent": user_agent},
        }
        data = await fetch(body, key)
        return to_rows(data, symbols)

    @staticmethod
    def transform_data(
        query: AuraStreamFailsToDeliverQueryParams, data: list[dict], **kwargs: Any
    ) -> list[AuraStreamFailsToDeliverData]:
        """Transform the data."""
        return [AuraStreamFailsToDeliverData.model_validate(d) for d in data]
