"""OpenBB AuraStream Provider Module."""

from openbb_core.provider.abstract.provider import Provider

from openbb_aurastream.models.fails_to_deliver import AuraStreamFailsToDeliverFetcher
from openbb_aurastream.models.fred_vintages import AuraStreamFredVintagesFetcher
from openbb_aurastream.models.funding_rates import AuraStreamFundingRatesFetcher
from openbb_aurastream.models.net_short import AuraStreamNetShortFetcher
from openbb_aurastream.models.wasde import AuraStreamWasdeFetcher

aurastream_provider = Provider(
    name="aurastream",
    website="https://aurastream.unbiased-alpha.com",
    description="AuraStream, a unified market data API for quants by Unbiased Alpha:"
    " EU net short positions, USDA WASDE projections, FRED with every revision,"
    " SEC fails-to-deliver and Binance funding rates.",
    credentials=["api_key", "fred_api_key", "sec_user_agent"],
    fetcher_dict={
        "AuraStreamNetShort": AuraStreamNetShortFetcher,
        "AuraStreamWasde": AuraStreamWasdeFetcher,
        "AuraStreamFredVintages": AuraStreamFredVintagesFetcher,
        "AuraStreamFailsToDeliver": AuraStreamFailsToDeliverFetcher,
        "AuraStreamFundingRates": AuraStreamFundingRatesFetcher,
    },
    repr_name="AuraStream",
    instructions="Get a free API key (500 calls a month, no credit card) at"
    " https://aurastream.unbiased-alpha.com/sign-up and set it as aurastream_api_key."
    " fred_vintages also needs your own free FRED key (aurastream_fred_api_key), and"
    " fails_to_deliver a contact string for the SEC (aurastream_sec_user_agent),"
    " e.g. 'Jane Doe jane@example.com'.",
)
