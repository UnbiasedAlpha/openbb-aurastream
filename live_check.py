"""Run each command once against the live AuraStream API (uses 5 calls).

Reads the key from the AURASTREAM_API_KEY environment variable; FRED and
fails-to-deliver run only when FRED_API_KEY / SEC_USER_AGENT are set too.
"""

import os

from openbb import obb

obb.user.credentials.aurastream_api_key = os.environ["AURASTREAM_API_KEY"]
if os.environ.get("FRED_API_KEY"):
    obb.user.credentials.aurastream_fred_api_key = os.environ["FRED_API_KEY"]
if os.environ.get("SEC_USER_AGENT"):
    obb.user.credentials.aurastream_sec_user_agent = os.environ["SEC_USER_AGENT"]

checks = {
    "net_short": lambda: obb.aurastream.net_short("ubisoft", start_date="2025-01-01", country="FR"),
    "wasde": lambda: obb.aurastream.wasde("corn:ending_stocks", start_date="2025-06-01"),
    "funding_rates": lambda: obb.aurastream.funding_rates("BTCUSDT", start_date="2025-06-01", end_date="2025-06-03"),
}
if os.environ.get("FRED_API_KEY"):
    checks["fred_vintages"] = lambda: obb.aurastream.fred_vintages("CPIAUCSL", start_date="2025-01-01", end_date="2025-04-01")
if os.environ.get("SEC_USER_AGENT"):
    checks["fails_to_deliver"] = lambda: obb.aurastream.fails_to_deliver("GME", start_date="2024-05-01", end_date="2024-06-01")

for name, call in checks.items():
    try:
        df = call().to_df()
        print(f"OK   {name}: {len(df)} rows, columns {list(df.columns)[:6]}")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {name}: {type(exc).__name__}: {str(exc)[:300]}")
