"""AuraStream FRED Vintages Model."""

from datetime import date as dateType, datetime
from typing import Any

from openbb_core.provider.abstract.data import Data
from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.bls_series import SeriesQueryParams
from openbb_core.provider.utils.errors import EmptyDataError
from pydantic import Field

from openbb_aurastream.utils.client import (
    api_key,
    default_start,
    fetch,
    parse_timestamp,
    require_key,
    split_symbols,
)


class AuraStreamFredVintagesQueryParams(SeriesQueryParams):
    """AuraStream FRED Vintages Query.

    Source: https://aurastream.unbiased-alpha.com/docs/data-sources/fred/
    """

    __json_schema_extra__ = {"symbol": {"multiple_items_allowed": True}}

    symbol: str = Field(
        description="FRED series ID, e.g. 'CPIAUCSL', 'UNRATE', 'GDPC1'."
    )
    start_date: dateType | None = Field(
        default=None,
        description="First publication date. Default: one year ago.",
    )
    end_date: dateType | None = Field(
        default=None, description="Last publication date. Default: today."
    )


class AuraStreamFredVintagesData(Data):
    """AuraStream FRED Vintages Data. One row per published value."""

    date: datetime = Field(description="Publication date of the value.")
    symbol: str = Field(description="FRED series ID.")
    reference_date: datetime = Field(description="The period the value describes.")
    value: float | None = Field(default=None, description="The value as published.")


class AuraStreamFredVintagesFetcher(
    Fetcher[AuraStreamFredVintagesQueryParams, list[AuraStreamFredVintagesData]]
):
    """Fetch every published version of FRED series from AuraStream."""

    require_credentials = False

    @staticmethod
    def transform_query(params: dict[str, Any]) -> AuraStreamFredVintagesQueryParams:
        """Transform the query."""
        return AuraStreamFredVintagesQueryParams(**params)

    @staticmethod
    async def aextract_data(
        query: AuraStreamFredVintagesQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Return one row per (publication date, period)."""
        key = api_key(credentials)
        fred_key = require_key(
            credentials,
            "aurastream_fred_api_key",
            "FRED needs a free key of your own: https://fred.stlouisfed.org/docs/api/api_key.html.",
        )
        symbols = [s.upper() for s in split_symbols(query.symbol)]
        body = {
            "tickerlist": symbols,
            "start": str(query.start_date or default_start()),
            "end": str(query.end_date or dateType.today()),
            "interval": "1d",  # ignored: each series comes at its own frequency
            "source": "fred",
            "credentials": {"key": fred_key},
        }
        data = await fetch(body, key)

        rows: list[dict] = []
        for symbol in symbols:
            series = data.get(symbol)
            if not isinstance(series, dict):
                continue
            for published, row in series.items():
                for update in (row or {}).get("updates") or []:
                    rows.append(
                        {
                            "date": parse_timestamp(published),
                            "symbol": symbol,
                            "reference_date": parse_timestamp(update["reference_date"]),
                            "value": update.get("value"),
                        }
                    )
        if not rows:
            raise EmptyDataError(f"AuraStream returned no data for {', '.join(symbols)}.")
        rows.sort(key=lambda r: (r["date"], r["symbol"], r["reference_date"]))
        return rows

    @staticmethod
    def transform_data(
        query: AuraStreamFredVintagesQueryParams, data: list[dict], **kwargs: Any
    ) -> list[AuraStreamFredVintagesData]:
        """Transform the data."""
        return [AuraStreamFredVintagesData.model_validate(d) for d in data]
