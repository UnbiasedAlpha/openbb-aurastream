"""Thin async client for the AuraStream /timeseries endpoint."""

import os
from datetime import date, datetime, timedelta
from typing import Any

from openbb_core.app.model.abstract.error import OpenBBError
from openbb_core.provider.utils.errors import EmptyDataError, UnauthorizedError

API_URL = os.environ.get(
    "AURASTREAM_API_URL", "https://api.aurastream.unbiased-alpha.com/timeseries"
)
DASHBOARD_URL = "https://aurastream.unbiased-alpha.com"
TIMEOUT_SECONDS = 130  # the API itself times out at 120 s


def default_start() -> date:
    """One year back, the default start of a query."""
    return date.today() - timedelta(days=365)


def require_key(credentials: dict[str, str] | None, name: str, hint: str) -> str:
    """Return a credential or raise an error saying how to set it."""
    value = (credentials or {}).get(name)
    if not value:
        raise UnauthorizedError(
            f"Missing credential '{name}'. {hint} Set it with "
            f'obb.user.credentials.{name} = "..." or in ~/.openbb_platform/user_settings.json.'
        )
    return value


def api_key(credentials: dict[str, str] | None) -> str:
    """The AuraStream API key."""
    return require_key(
        credentials,
        "aurastream_api_key",
        f"Get a free key (500 calls a month, no credit card) at {DASHBOARD_URL}/sign-up.",
    )


def _error_message(status: int, detail: str) -> str:
    if status == 429:
        if "limit exceeded" in detail.lower():
            return (
                "AuraStream monthly call allowance is used up. It resets on the 1st of next month "
                f"(00:00 UTC); to keep going now, upgrade the plan at {DASHBOARD_URL}."
            )
        return "AuraStream rate limit hit. Wait a few seconds and retry."
    if status in (401, 403):
        return (
            f"AuraStream rejected the API key (HTTP {status}). "
            f"Check aurastream_api_key; keys are on the dashboard at {DASHBOARD_URL}."
        )
    if status == 400:
        return f"AuraStream rejected the request (HTTP 400): {detail or 'no detail'}."
    if status in (502, 504):
        return (
            f"AuraStream timed out (HTTP {status}). "
            "Try a shorter date range or fewer symbols."
        )
    return f"AuraStream returned HTTP {status}: {detail or 'no detail'}"


async def fetch(body: dict[str, Any], key: str) -> dict[str, Any]:
    """POST the body to AuraStream and return the parsed JSON."""
    import aiohttp

    timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                API_URL, json=body, headers={"x-api-key": key}
            ) as resp:
                status = resp.status
                text = await resp.text()
    except TimeoutError:
        raise OpenBBError(
            "AuraStream did not answer in time. Try a shorter date range or fewer symbols."
        ) from None
    except aiohttp.ClientError as exc:
        raise OpenBBError(f"Could not reach AuraStream: {exc}") from None

    import json

    try:
        data = json.loads(text)
    except ValueError:
        data = None

    if status != 200:
        detail = ""
        if isinstance(data, dict):
            detail = str(
                data.get("message") or data.get("error") or data.get("detail") or ""
            )
        elif text:
            detail = text.strip()
        message = _error_message(status, detail[:300])
        if status in (401, 403):
            raise UnauthorizedError(message)
        raise OpenBBError(message)

    if not isinstance(data, dict):
        raise OpenBBError("AuraStream returned a response that is not a JSON object.")
    # Errors that come back with a 200, e.g. {"error": "..."}.
    if len(data) == 1:
        k, v = next(iter(data.items()))
        if k in ("error", "message") and isinstance(v, str):
            raise OpenBBError(f"AuraStream error: {v[:300]}")
    return data


def parse_timestamp(value: str) -> datetime:
    """Parse a row key such as '2025-02-12 00:00:00' or '2025-02-12 00:00:00.000001'."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def to_rows(data: dict[str, Any], symbols: list[str]) -> list[dict[str, Any]]:
    """Flatten {symbol: {timestamp: fields}} into rows with 'date' and 'symbol'.

    Raises EmptyDataError when no symbol returned any row.
    """
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for symbol in symbols:
        series = data.get(symbol)
        if isinstance(series, str):
            errors.append(f"{symbol}: {series[:200]}")
            continue
        if not isinstance(series, dict):
            continue
        for ts, fields in series.items():
            if not isinstance(fields, dict):
                continue
            row = {"date": parse_timestamp(ts), "symbol": symbol}
            row.update(fields)
            rows.append(row)
    if not rows:
        extra = f" ({'; '.join(errors)})" if errors else ""
        raise EmptyDataError(f"AuraStream returned no data for {', '.join(symbols)}{extra}.")
    rows.sort(key=lambda r: (r["date"], r["symbol"]))
    return rows


def split_symbols(symbol: str) -> list[str]:
    """'a, b' -> ['a', 'b']."""
    return [s.strip() for s in symbol.split(",") if s.strip()]
