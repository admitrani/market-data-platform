"""Typed domain models for raw market data ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Kline(BaseModel):
    """Typed representation of one Binance kline/candlestick row.

    Binance raw API returns lists with stringified numeric values.
    This model converts them into explicit Python types and validates
    basic OHLCV integrity before the row can enter raw storage.
    """

    model_config = ConfigDict(frozen=True)

    open_time_ms: int = Field(ge=0)
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    close_time_ms: int = Field(ge=0)
    quote_asset_volume: float = Field(ge=0)
    number_of_trades: int = Field(ge=0)
    taker_buy_base_asset_volume: float = Field(ge=0)
    taker_buy_quote_asset_volume: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_ohlcv_consistency(self) -> "Kline":
        if self.high < max(self.open, self.close):
            raise ValueError("high must be >= max(open, close)")

        if self.low > min(self.open, self.close):
            raise ValueError("low must be <= min(open, close)")

        if self.close_time_ms <= self.open_time_ms:
            raise ValueError("close_time_ms must be > open_time_ms")

        return self

    @property
    def open_datetime_utc(self) -> datetime:
        return datetime.fromtimestamp(self.open_time_ms / 1000, tz=timezone.utc)

    @property
    def close_datetime_utc(self) -> datetime:
        return datetime.fromtimestamp(self.close_time_ms / 1000, tz=timezone.utc)

    @classmethod
    def from_binance_row(cls, row: list[Any]) -> "Kline":
        """Build a typed Kline from Binance's raw REST API payload.

        Expected Binance kline format:
        [
            open_time,
            open,
            high,
            low,
            close,
            volume,
            close_time,
            quote_asset_volume,
            number_of_trades,
            taker_buy_base_asset_volume,
            taker_buy_quote_asset_volume,
            ignore
        ]
        """

        if len(row) < 11:
            raise ValueError(f"Expected at least 11 fields from Binance kline row, got {len(row)}")

        return cls(
            open_time_ms=int(row[0]),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
            close_time_ms=int(row[6]),
            quote_asset_volume=float(row[7]),
            number_of_trades=int(row[8]),
            taker_buy_base_asset_volume=float(row[9]),
            taker_buy_quote_asset_volume=float(row[10]),
        )
