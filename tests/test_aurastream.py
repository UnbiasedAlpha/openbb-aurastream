"""Tests for the AuraStream fetchers, against a local stand-in for the API."""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from openbb_core.app.model.abstract.error import OpenBBError
from openbb_core.provider.utils.errors import EmptyDataError, UnauthorizedError

from openbb_aurastream.models.fails_to_deliver import AuraStreamFailsToDeliverFetcher
from openbb_aurastream.models.fred_vintages import AuraStreamFredVintagesFetcher
from openbb_aurastream.models.funding_rates import AuraStreamFundingRatesFetcher
from openbb_aurastream.models.net_short import AuraStreamNetShortFetcher
from openbb_aurastream.models.wasde import AuraStreamWasdeFetcher
from openbb_aurastream.utils import client

CREDS = {
    "aurastream_api_key": "test-key",
    "aurastream_fred_api_key": "test-fred",
    "aurastream_sec_user_agent": "Test test@example.com",
}


class FakeApi:
    """Records the last request and answers with a canned response."""

    def __init__(self):
        self.status = 200
        self.payload: object = {}
        self.body: dict = {}
        self.headers: dict = {}


@pytest.fixture
def api(monkeypatch):
    fake = FakeApi()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers["Content-Length"])
            fake.body = json.loads(self.rfile.read(length))
            fake.headers = dict(self.headers)
            out = json.dumps(fake.payload).encode()
            self.send_response(fake.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(client, "API_URL", f"http://127.0.0.1:{server.server_port}/timeseries")
    yield fake
    server.shutdown()


def run(fetcher, params, credentials=CREDS):
    return asyncio.run(fetcher.fetch_data(params, credentials))


def test_net_short(api):
    api.payload = {
        "ubisoft": {
            "2025-03-04 00:00:00": {
                "holder": "Fund A",
                "issuer": "UBISOFT ENTERTAINMENT",
                "isin": "FR0000054470",
                "net_short_pct": 0.62,
                "country": "FR",
            },
            "2025-03-04 00:00:00.000001": {
                "holder": "Fund B",
                "issuer": "UBISOFT ENTERTAINMENT",
                "isin": "FR0000054470",
                "net_short_pct": 1.1,
                "country": "FR",
            },
        }
    }
    rows = run(
        AuraStreamNetShortFetcher,
        {"symbol": "ubisoft", "start_date": "2025-01-01", "end_date": "2025-06-01",
         "country": "fr,NL", "holder": "fund"},
    )
    assert api.headers["x-api-key"] == "test-key"
    assert api.body == {
        "tickerlist": ["ubisoft"], "start": "2025-01-01", "end": "2025-06-01",
        "interval": "1d", "source": "netshort", "country": ["FR", "NL"], "holder": "fund",
    }
    assert [r.holder for r in rows] == ["Fund A", "Fund B"]
    assert rows[1].net_short_pct == 1.1
    assert rows[0].symbol == "ubisoft"


def test_wasde(api):
    api.payload = {
        "corn:ending_stocks": {
            "2026-10-09 12:00:00-04:00": {
                "market_year": "2026/27", "value": 2110, "previous": 2120,
                "prior_year": "2025/26", "prior_year_value": 1530, "report": "October 2026",
            }
        }
    }
    rows = run(AuraStreamWasdeFetcher, {"symbol": "corn:ending_stocks", "start_date": "2026-01-01"})
    assert api.body["source"] == "wasde" and api.body["interval"] == "1m"
    assert api.body["start"] == "2026-01-01"
    assert rows[0].value == 2110 and rows[0].previous == 2120
    assert rows[0].date.utcoffset() is not None


def test_fred_vintages_flattens_updates(api):
    api.payload = {
        "CPIAUCSL": {
            "2025-02-12 00:00:00": {"updates": [
                {"reference_date": "2025-01-01 00:00:00", "value": 317.671},
            ]},
            "2025-03-12 00:00:00": {"updates": [
                {"reference_date": "2025-01-01 00:00:00", "value": 317.7},
                {"reference_date": "2025-02-01 00:00:00", "value": 318.5},
            ]},
        }
    }
    rows = run(AuraStreamFredVintagesFetcher, {"symbol": "cpiaucsl"})
    assert api.body["credentials"] == {"key": "test-fred"}
    assert api.body["tickerlist"] == ["CPIAUCSL"]
    assert [(r.date.month, r.reference_date.month, r.value) for r in rows] == [
        (2, 1, 317.671), (3, 1, 317.7), (3, 2, 318.5),
    ]


def test_fred_needs_fred_key(api):
    creds = {"aurastream_api_key": "test-key"}
    with pytest.raises(UnauthorizedError, match="aurastream_fred_api_key"):
        run(AuraStreamFredVintagesFetcher, {"symbol": "UNRATE"}, creds)


def test_fails_to_deliver(api):
    api.payload = {
        "GME": {
            "2024-05-15 00:00:00": {
                "fails": "1200345", "price": "23.1", "symbol": "GME",
                "cusip": "36467W109", "description": "GAMESTOP CORP CL A",
            }
        }
    }
    rows = run(AuraStreamFailsToDeliverFetcher, {"symbol": "gme"})
    assert api.body["dataset"] == "ftd" and api.body["source"] == "edgar"
    assert api.body["credentials"] == {"user_agent": "Test test@example.com"}
    assert rows[0].fails == 1200345 and rows[0].price == 23.1


def test_funding_rates_multiple_symbols(api):
    api.payload = {
        "BTCUSDT": {"2025-06-01 08:00:00": {"fundingRate": "0.0001"}},
        "ETHUSDT": {"2025-06-01 00:00:00": {"fundingRate": "-0.00005"}},
    }
    rows = run(AuraStreamFundingRatesFetcher, {"symbol": "btcusdt,ethusdt"})
    assert api.body["bars"] == "funding" and api.body["instrument"] == "futures"
    assert [(r.symbol, r.funding_rate) for r in rows] == [("ETHUSDT", -0.00005), ("BTCUSDT", 0.0001)]


def test_missing_api_key():
    with pytest.raises(UnauthorizedError, match="aurastream_api_key"):
        run(AuraStreamWasdeFetcher, {"symbol": "corn:ending_stocks"}, {})


def test_rejected_key(api):
    api.status = 403
    api.payload = {"message": "Forbidden"}
    with pytest.raises(UnauthorizedError, match="rejected the API key"):
        run(AuraStreamWasdeFetcher, {"symbol": "corn:ending_stocks"})


def test_allowance_used_up(api):
    api.status = 429
    api.payload = {"message": "Limit Exceeded"}
    with pytest.raises(OpenBBError, match="allowance is used up"):
        run(AuraStreamWasdeFetcher, {"symbol": "corn:ending_stocks"})


def test_error_with_200(api):
    api.payload = {"error": "Unknown region 'Atlantis'"}
    with pytest.raises(OpenBBError, match="Atlantis"):
        run(AuraStreamWasdeFetcher, {"symbol": "corn:production:Atlantis"})


def test_empty(api):
    api.payload = {"corn:ending_stocks": {}}
    with pytest.raises(EmptyDataError):
        run(AuraStreamWasdeFetcher, {"symbol": "corn:ending_stocks"})


def test_obb_end_to_end(api):
    from openbb import obb

    api.payload = {"BTCUSDT": {"2025-06-01 08:00:00": {"fundingRate": "0.0001"}}}
    obb.user.credentials.aurastream_api_key = "test-key"
    df = obb.aurastream.funding_rates("BTCUSDT").to_df()
    assert df["funding_rate"].iloc[0] == 0.0001


def test_obb_keeps_case_and_takes_lists(api):
    from openbb import obb

    api.payload = {
        "corn:ending_stocks": {"2026-10-09 12:00:00": {"value": 2110}},
        "soybeans:production:Brazil": {"2026-10-09 12:00:00": {"value": 175}},
    }
    obb.user.credentials.aurastream_api_key = "test-key"
    out = obb.aurastream.wasde(["corn:ending_stocks", "soybeans:production:Brazil"])
    assert api.body["tickerlist"] == ["corn:ending_stocks", "soybeans:production:Brazil"]
    assert len(out.results) == 2
