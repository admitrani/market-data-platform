"""Ingestion pipeline orchestration for raw market data backfills and incrementals."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol

from ingestion.models import Kline
from ingestion.state.watermark import Watermark, new_watermark
from ingestion.storage.gcs_raw import GCSWriteResult, RawPartitionSpec


class BinanceKlineClientLike(Protocol):
    def fetch_klines(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
        limit: int = 1000,
    ) -> list[Kline]: ...


class RawWriterLike(Protocol):
    def write_klines_partition(
        self,
        rows: Sequence[Kline],
        spec: RawPartitionSpec,
        loaded_at: datetime | None = None,
        batch_id: str | None = None,
    ) -> GCSWriteResult: ...


class WatermarkStoreLike(Protocol):
    def read(
        self,
        *,
        source: str,
        dataset: str,
        symbol: str,
        interval: str,
    ) -> Watermark | None: ...

    def write(self, watermark: Watermark) -> None: ...


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
class IncrementalRequest:
    """Incremental ingestion request bounded by an explicit end date."""

    source: str
    dataset: str
    symbol: str
    interval: str
    bootstrap_start_date: date
    end_date: date
    limit: int = 1000

    def validate(self) -> None:
        if self.bootstrap_start_date > self.end_date:
            raise ValueError("bootstrap_start_date must be <= end_date")

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


@dataclass(frozen=True)
class IncrementalResult:
    """Summary of one incremental execution."""

    request: IncrementalRequest
    start_date_used: date
    partitions_written: int
    rows_written: int
    watermark_before: Watermark | None
    watermark_after: Watermark | None
    outputs: tuple[GCSWriteResult, ...]


class IngestionPipeline:
    """Coordinates fetching Binance klines and writing raw GCS partitions."""

    def __init__(
        self,
        client: BinanceKlineClientLike,
        writer: RawWriterLike,
        watermark_store: WatermarkStoreLike | None = None,
    ) -> None:
        self.client = client
        self.writer = writer
        self.watermark_store = watermark_store

    def run_backfill(self, request: BackfillRequest) -> BackfillResult:
        """Run an inclusive date-range backfill."""

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

    def run_incremental(self, request: IncrementalRequest) -> IncrementalResult:
        """Run incremental ingestion using a GCS-backed watermark.

        Phase 1 uses daily partition semantics:
        - if no watermark exists, start from bootstrap_start_date
        - if watermark exists, start from the day after the last completed partition
        """

        request.validate()

        if self.watermark_store is None:
            raise ValueError("watermark_store is required for incremental ingestion")

        watermark_before = self.watermark_store.read(
            source=request.source,
            dataset=request.dataset,
            symbol=request.symbol,
            interval=request.interval,
        )

        if watermark_before is None:
            start_date = request.bootstrap_start_date
        else:
            start_date = _utc_date_from_ms(watermark_before.last_open_time_ms) + timedelta(days=1)

        if start_date > request.end_date:
            return IncrementalResult(
                request=request,
                start_date_used=start_date,
                partitions_written=0,
                rows_written=0,
                watermark_before=watermark_before,
                watermark_after=watermark_before,
                outputs=tuple(),
            )

        backfill_result = self.run_backfill(
            BackfillRequest(
                source=request.source,
                dataset=request.dataset,
                symbol=request.symbol,
                interval=request.interval,
                start_date=start_date,
                end_date=request.end_date,
                limit=request.limit,
            )
        )

        watermark_after: Watermark | None = watermark_before

        if backfill_result.outputs:
            max_open_time_ms = max(output.max_open_time_ms for output in backfill_result.outputs)

            watermark_after = new_watermark(
                source=request.source,
                dataset=request.dataset,
                symbol=request.symbol,
                interval=request.interval,
                last_open_time_ms=max_open_time_ms,
            )

            self.watermark_store.write(watermark_after)

        return IncrementalResult(
            request=request,
            start_date_used=start_date,
            partitions_written=backfill_result.partitions_written,
            rows_written=backfill_result.rows_written,
            watermark_before=watermark_before,
            watermark_after=watermark_after,
            outputs=backfill_result.outputs,
        )


def _iter_dates_inclusive(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _utc_date_start_ms(value: date) -> int:
    dt = datetime.combine(value, time.min, tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def _utc_date_from_ms(value: int) -> date:
    return datetime.fromtimestamp(value / 1000, tz=UTC).date()
