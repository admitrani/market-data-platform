from __future__ import annotations

from typing import Any

import pytest

from ingestion.clients.binance_spot import BinanceSpotClient
from ingestion.models import Kline


SAMPLE_KLINE = [
    1704067200000,
    "42283.58000000",
    "42554.57000000",
    "42180.00000000",
    "42475.23000000",
    "1271.68156000",
    1704070799999,
    "53978544.71370080",
    43921,
    "658.12075000",
    "27936997.40174620",
    "0",
]


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, params: dict[str, Any], timeout: int) -> FakeResponse:
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return self.responses.pop(0)


def test_kline_from_binance_row_parses_api_payload() -> None:
    kline = Kline.from_binance_row(SAMPLE_KLINE)

    assert kline.open_time_ms == 1704067200000
    assert kline.open == 42283.58
    assert kline.high == 42554.57
    assert kline.low == 42180.0
    assert kline.close == 42475.23
    assert kline.number_of_trades == 43921


def test_kline_rejects_invalid_ohlcv_relationship() -> None:
    invalid = SAMPLE_KLINE.copy()
    invalid[2] = "42000.00000000"  # high lower than open/close

    with pytest.raises(ValueError, match="high must be"):
        Kline.from_binance_row(invalid)


def test_client_fetch_klines_returns_typed_models() -> None:
    session = FakeSession([FakeResponse(status_code=200, payload=[SAMPLE_KLINE])])
    client = BinanceSpotClient(session=session)

    rows = client.fetch_klines(
        symbol="BTCUSDT",
        interval="1h",
        start_ms=1704067200000,
        end_ms=1704070800000,
    )

    assert len(rows) == 1
    assert isinstance(rows[0], Kline)

    call = session.calls[0]
    assert call["url"] == "https://api.binance.com/api/v3/klines"
    assert call["params"]["symbol"] == "BTCUSDT"
    assert call["params"]["interval"] == "1h"
    assert call["params"]["limit"] == 1000
    assert call["timeout"] == 30


def test_client_retries_after_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ingestion.clients.binance_spot.time.sleep", lambda _: None)

    session = FakeSession(
        [
            FakeResponse(status_code=429, payload=None, headers={"Retry-After": "1"}),
            FakeResponse(status_code=200, payload=[SAMPLE_KLINE]),
        ]
    )
    client = BinanceSpotClient(session=session, max_retries=2)

    rows = client.fetch_klines(
        symbol="BTCUSDT",
        interval="1h",
        start_ms=1704067200000,
        end_ms=1704070800000,
    )

    assert len(rows) == 1
    assert len(session.calls) == 2


def test_client_rejects_invalid_time_range() -> None:
    client = BinanceSpotClient(session=FakeSession([]))

    with pytest.raises(ValueError, match="start_ms must be lower"):
        client.fetch_klines(
            symbol="BTCUSDT",
            interval="1h",
            start_ms=1704070800000,
            end_ms=1704067200000,
        )
