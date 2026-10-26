"""AuraStream Router."""

from openbb_core.app.model.command_context import CommandContext
from openbb_core.app.model.example import APIEx
from openbb_core.app.model.obbject import OBBject
from openbb_core.app.provider_interface import (
    ExtraParams,
    ProviderChoices,
    StandardParams,
)
from openbb_core.app.query import Query
from openbb_core.app.router import Router

router = Router(prefix="", description="AuraStream market data.")


@router.command(
    model="AuraStreamNetShort",
    examples=[
        APIEx(
            description="Disclosed short positions in Ubisoft on the French register.",
            parameters={"symbol": "ubisoft", "country": "FR", "provider": "aurastream"},
        ),
        APIEx(
            description="Every position one fund has disclosed in the period.",
            parameters={"symbol": "all", "holder": "citadel", "provider": "aurastream"},
        ),
    ],
)
async def net_short(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Get disclosed net short positions of 0.5% or more in European shares (AMF, AFM, CNMV)."""
    return await OBBject.from_query(Query(**locals()))


@router.command(
    model="AuraStreamWasde",
    examples=[
        APIEx(
            description="How the USDA's projection of US corn ending stocks changed, report by report.",
            parameters={"symbol": "corn:ending_stocks", "provider": "aurastream"},
        ),
        APIEx(
            description="Brazil's soybean crop from the world tables.",
            parameters={"symbol": "soybeans:production:Brazil", "provider": "aurastream"},
        ),
    ],
)
async def wasde(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Get USDA WASDE projections since July 2010, one row per monthly report."""
    return await OBBject.from_query(Query(**locals()))


@router.command(
    model="AuraStreamFredVintages",
    examples=[
        APIEx(
            description="Every published version of US CPI, by publication date.",
            parameters={"symbol": "CPIAUCSL", "provider": "aurastream"},
        ),
    ],
)
async def fred_vintages(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Get FRED series with every revision, stamped at the date each value was published."""
    return await OBBject.from_query(Query(**locals()))


@router.command(
    model="AuraStreamFailsToDeliver",
    examples=[
        APIEx(
            description="Fails-to-deliver in GameStop.",
            parameters={"symbol": "GME", "provider": "aurastream"},
        ),
    ],
)
async def fails_to_deliver(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Get SEC fails-to-deliver for a US stock or ETF, one row per settlement date."""
    return await OBBject.from_query(Query(**locals()))


@router.command(
    model="AuraStreamFundingRates",
    examples=[
        APIEx(
            description="Funding rates of the Bitcoin and Ether perpetuals.",
            parameters={"symbol": "BTCUSDT,ETHUSDT", "provider": "aurastream"},
        ),
    ],
)
async def funding_rates(
    cc: CommandContext,
    provider_choices: ProviderChoices,
    standard_params: StandardParams,
    extra_params: ExtraParams,
) -> OBBject:
    """Get Binance USD-M perpetual funding rates at each funding time."""
    return await OBBject.from_query(Query(**locals()))
