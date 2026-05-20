"""Binance Spot REST client for market data ingestion."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from ingestion.models import Kline

logger = logging.getLogger(__name__)


class BinanceSpotClient:
    """Small Binance Spot REST client with retry/backoff.

    This client is intentionally narrow for Phase 1:
    - endpoint: /api/v3/klines
    - output: typed Kline objects
    - no API key needed for public market data
    """

    def __init__(
        self,
        base_url: str = "https://api.binance.com",
        timeout_seconds: int = 30,
        max_retries: int = 5,
        backoff_seconds: int = 2,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.session = session or requests.Session()

    def fetch_klines(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
        limit: int = 1000,
    ) -> list[Kline]:
        """Fetch klines from Binance and return validated typed rows."""

        if start_ms >= end_ms:
            raise ValueError("start_ms must be lower than end_ms")

        if limit <= 0 or limit > 1000:
            raise ValueError("Binance kline limit must be between 1 and 1000")

        url = f"{self.base_url}/api/v3/klines"
        params: dict[str, Any] = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": limit,
        }

        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "Fetching Binance klines",
                    extra={
                        "symbol": symbol,
                        "interval": interval,
                        "start_ms": start_ms,
                        "end_ms": end_ms,
                        "limit": limit,
                        "attempt": attempt,
                    },
                )

                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout_seconds,
                )

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    sleep_seconds = (
                        int(retry_after) if retry_after else self.backoff_seconds * attempt
                    )

                    logger.warning(
                        "Binance rate limit hit; backing off",
                        extra={"attempt": attempt, "sleep_seconds": sleep_seconds},
                    )

                    time.sleep(sleep_seconds)
                    continue

                if response.status_code >= 500:
                    logger.warning(
                        "Binance server error; retrying",
                        extra={"status_code": response.status_code, "attempt": attempt},
                    )
                    time.sleep(self.backoff_seconds * attempt)
                    continue

                response.raise_for_status()
                payload = response.json()

                if not isinstance(payload, list):
                    raise ValueError("Expected Binance klines response to be a list")

                return [Kline.from_binance_row(row) for row in payload]

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                logger.warning(
                    "Network error while fetching Binance klines; retrying",
                    extra={"attempt": attempt, "error": str(exc)},
                )
                time.sleep(self.backoff_seconds * attempt)

            except requests.RequestException as exc:
                last_error = exc
                logger.warning(
                    "Request error while fetching Binance klines; retrying",
                    extra={"attempt": attempt, "error": str(exc)},
                )
                time.sleep(self.backoff_seconds * attempt)

        raise RuntimeError(
            f"Failed to fetch Binance klines after {self.max_retries} attempts"
        ) from last_error
