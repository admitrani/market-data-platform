"""Ingestion pipeline orchestration for raw market data backfills."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Protocol, Sequence

from ingestion.models import Kline
from ingestion.storage.gcs_raw import GCSWriteResult, RawPartitionSpec


class BinanceKlineClientLike(Protocol):
    def fetch_klines(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
        limit: int = 1000,
    ) -> list[Kline]:
        ...


class RawWriterLike(Protocol):
    def write_klines_partition(
        self,
        rows: Sequence[Kline],
        spec: RawPartitionSpec,
        loaded_at: datetime | None = None,
        batch_id: str | None = None,
    ) -> GCSWriteResult:
        ...


@dataclass(frozen=True)
class BackfillRequest:
    """Backfill request for one source/dataset/symbol/interval."""

    source: str
    dataset: str
    symbol: str
    interval: str
    start_date: date
    end_date: date
    limit: int = 1000

    def validate(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError("start_date must be <= end_date")

        if self.limit <= 0 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")

        if self.interval != "1h":
            raise ValueError("Phase 1 CORE only supports interval='1h'")


@dataclass(frozen=True)
class BackfillResult:
    """Summary of one backfill execution."""

    request: BackfillRequest
    partitions_written: int
    rows_written: int
    outputs: tuple[GCSWriteResult, ...]


class IngestionPipeline:
    """Coordinates fetching Binance klines and writing raw GCS partitions."""

    def __init__(
        self,
        client: BinanceKlineClientLike,
        writer: RawWriterLike,
    ) -> None:
        self.client = client
        self.writer = writer

    def run_backfill(self, request: BackfillRequest) -> BackfillResult:
        """Run an inclusive date-range backfill.

        Both start_date and end_date are inclusive.

        Example:
        start_date=2024-01-01, end_date=2024-01-03
        writes:
        - date=2024-01-01
        - date=2024-01-02
        - date=2024-01-03
        """

        request.validate()

        outputs: list[GCSWriteResult] = []

        for partition_date in _iter_dates_inclusive(request.start_date, request.end_date):
            start_ms = _utc_date_start_ms(partition_date)
            end_ms = _utc_date_start_ms(partition_date + timedelta(days=1)) - 1

            rows = self.client.fetch_klines(
                symbol=request.symbol,
                interval=request.interval,
                start_ms=start_ms,
                end_ms=end_ms,
                limit=request.limit,
            )

            if not rows:
                continue

            spec = RawPartitionSpec(
                source=request.source,
                dataset=request.dataset,
                symbol=request.symbol,
                interval=request.interval,
                partition_date=partition_date,
            )

            outputs.append(
                self.writer.write_klines_partition(
                    rows=rows,
                    spec=spec,
                )
            )

        return BackfillResult(
            request=request,
            partitions_written=len(outputs),
            rows_written=sum(output.row_count for output in outputs),
            outputs=tuple(outputs),
        )


def _iter_dates_inclusive(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _utc_date_start_ms(value: date) -> int:
    dt = datetime.combine(value, time.min, tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)
