# openbb-aurastream

[AuraStream](https://aurastream.unbiased-alpha.com) data for the [OpenBB Platform](https://github.com/OpenBB-finance/OpenBB). The extension adds five commands under `obb.aurastream`. Each covers a dataset that the other OpenBB providers don't offer:

| Command | Data |
|---|---|
| `net_short` | EU net short positions of 0.5% or more, with the holder's name, from the French (AMF), Dutch (AFM) and Spanish (CNMV) registers, back to 2010–2012 |
| `wasde` | USDA WASDE projections since July 2010: US balance sheets and world tables by country, one row per monthly report |
| `fred_vintages` | FRED series with every revision, stamped at the date each value was published |
| `fails_to_deliver` | SEC fails-to-deliver for any US stock or ETF |
| `funding_rates` | Binance USD-M perpetual funding rates |

## Install

```
pip install openbb openbb-aurastream
```

OpenBB rebuilds its Python interface the first time you import it after installing.

## Credentials

You need an AuraStream API key. The free plan includes 500 calls a month, with no credit card required: [sign up here](https://aurastream.unbiased-alpha.com/sign-up).

```python
from openbb import obb

obb.user.credentials.aurastream_api_key = "..."
# Only for fred_vintages: your own free FRED key (https://fred.stlouisfed.org/docs/api/api_key.html)
obb.user.credentials.aurastream_fred_api_key = "..."
# Only for fails_to_deliver: the SEC asks automated requests to name the sender
obb.user.credentials.aurastream_sec_user_agent = "Jane Doe jane@example.com"
```

You can also keep them in `~/.openbb_platform/user_settings.json`.

## Examples

```python
from openbb import obb

# Who is short Ubisoft, and by how much
shorts = obb.aurastream.net_short("ubisoft", start_date="2024-01-01", country="FR").to_df()
shorts.pivot_table(index=shorts.index.date, columns="holder", values="net_short_pct").ffill()

# Every position one fund has disclosed
obb.aurastream.net_short("all", holder="citadel", start_date="2026-01-01").to_df()

# How the USDA's projection of US corn ending stocks changed, report by report
corn = obb.aurastream.wasde("corn:ending_stocks", start_date="2024-01-01").to_df()
corn["revision"] = corn["value"] - corn["previous"]

# Brazil's soybean crop from the world tables
obb.aurastream.wasde("soybeans:production:Brazil").to_df()

# CPI as first published vs. after revisions
cpi = obb.aurastream.fred_vintages("CPIAUCSL", start_date="2020-01-01").to_df()
first_print = cpi.groupby("reference_date")["value"].first()
latest = cpi.groupby("reference_date")["value"].last()

# Fails-to-deliver in GameStop
obb.aurastream.fails_to_deliver("GME", start_date="2024-01-01", end_date="2025-01-01").to_df()

# Funding rates of the Bitcoin and Ether perpetuals
obb.aurastream.funding_rates("BTCUSDT,ETHUSDT", start_date="2025-06-01").to_df()
```

Without `start_date`, each command returns the last year.

## Timing

All five datasets are historical, not real-time, and each row is stamped when the data became public:

- EU net short positions are published by the next trading day, so lag them by one day in a backtest.
- WASDE rows are stamped at the report's release, 12:00 New York time.
- For `fred_vintages`, `start_date` and `end_date` filter on the publication date.
- The SEC publishes fails-to-deliver twice a month, about two weeks after each half-month ends.

See the [AuraStream docs](https://aurastream.unbiased-alpha.com/docs/) for the field definitions and coverage of each source.

## Data terms

- France: source Autorité des marchés financiers (AMF), data.gouv.fr, Licence Ouverte 2.0.
- Netherlands: source AFM.
- Spain: this information can be obtained free of charge from the CNMV website (www.cnmv.es).
- Holder names can belong to individuals, so treat them as personal data under the GDPR.

## License

MIT. This package is by Unbiased Alpha and is not affiliated with OpenBB.
