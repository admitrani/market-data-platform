from __future__ import annotations

from datetime import date, datetime
from typing import Sequence

import pytest

from ingestion.models import Kline
from ingestion.pipeline import BackfillRequest, IngestionPipeline, _utc_date_start_ms
from ingestion.storage.gcs_raw import GCSWriteResult, RawPartitionSpec


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


def make_kline(open_time_ms: int) -> Kline:
    row = SAMPLE_KLINE.copy()
    row[0] = open_time_ms
    row[6] = open_time_ms + 3_599_999
    return Kline.from_binance_row(row)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def fetch_klines(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
        limit: int = 1000,
    ) -> list[Kline]:
        self.calls.append(
            {
                "symbol": symbol,
                "interval": interval,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "limit": limit,
            }
        )
        return [make_kline(start_ms)]


class FakeWriter:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def write_klines_partition(
        self,
        rows: Sequence[Kline],
        spec: RawPartitionSpec,
        loaded_at: datetime | None = None,
        batch_id: str | None = None,
    ) -> GCSWriteResult:
        self.calls.append({"rows": rows, "spec": spec})
        return GCSWriteResult(
            bucket_name="test-bucket",
            object_path=spec.object_path,
            row_count=len(rows),
            min_open_time_ms=min(row.open_time_ms for row in rows),
            max_open_time_ms=max(row.open_time_ms for row in rows),
        )


def test_backfill_runs_inclusive_daily_partitions() -> None:
    client = FakeClient()
    writer = FakeWriter()
    pipeline = IngestionPipeline(client=client, writer=writer)

    result = pipeline.run_backfill(
        BackfillRequest(
            source="binance_spot",
            dataset="klines",
            symbol="BTCUSDT",
            interval="1h",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 3),
        )
    )

    assert result.partitions_written == 3
    assert result.rows_written == 3
    assert len(client.calls) == 3
    assert len(writer.calls) == 3

    assert client.calls[0]["start_ms"] == _utc_date_start_ms(date(2024, 1, 1))
    assert client.calls[1]["start_ms"] == _utc_date_start_ms(date(2024, 1, 2))
    assert client.calls[2]["start_ms"] == _utc_date_start_ms(date(2024, 1, 3))

    written_dates = [call["spec"].partition_date for call in writer.calls]
    assert written_dates == [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]


def test_backfill_skips_empty_partitions() -> None:
    class EmptyClient(FakeClient):
        def fetch_klines(
            self,
            symbol: str,
            interval: str,
            start_ms: int,
            end_ms: int,
            limit: int = 1000,
        ) -> list[Kline]:
            self.calls.append(
                {
                    "symbol": symbol,
                    "interval": interval,
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                    "limit": limit,
                }
            )
            return []

    client = EmptyClient()
    writer = FakeWriter()
    pipeline = IngestionPipeline(client=client, writer=writer)

    result = pipeline.run_backfill(
        BackfillRequest(
            source="binance_spot",
            dataset="klines",
            symbol="BTCUSDT",
            interval="1h",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
        )
    )

    assert result.partitions_written == 0
    assert result.rows_written == 0
    assert len(client.calls) == 1
    assert len(writer.calls) == 0


def test_backfill_rejects_unsupported_interval_for_phase_1_core() -> None:
    pipeline = IngestionPipeline(client=FakeClient(), writer=FakeWriter())

    with pytest.raises(ValueError, match="Phase 1 CORE only supports"):
        pipeline.run_backfill(
            BackfillRequest(
                source="binance_spot",
                dataset="klines",
                symbol="BTCUSDT",
                interval="1m",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 1),
            )
        )


def test_backfill_rejects_invalid_date_range() -> None:
    pipeline = IngestionPipeline(client=FakeClient(), writer=FakeWriter())

    with pytest.raises(ValueError, match="start_date must be"):
        pipeline.run_backfill(
            BackfillRequest(
                source="binance_spot",
                dataset="klines",
                symbol="BTCUSDT",
                interval="1h",
                start_date=date(2024, 1, 2),
                end_date=date(2024, 1, 1),
            )
        )


class FakeWatermarkStore:
    def __init__(self, watermark: object | None = None) -> None:
        self.watermark = watermark
        self.writes: list[object] = []

    def read(
        self,
        *,
        source: str,
        dataset: str,
        symbol: str,
        interval: str,
    ):
        return self.watermark

    def write(self, watermark) -> None:
        self.watermark = watermark
        self.writes.append(watermark)


def test_incremental_uses_bootstrap_date_when_no_watermark() -> None:
    client = FakeClient()
    writer = FakeWriter()
    watermark_store = FakeWatermarkStore()

    pipeline = IngestionPipeline(
        client=client,
        writer=writer,
        watermark_store=watermark_store,
    )

    result = pipeline.run_incremental(
        __import__("ingestion.pipeline", fromlist=["IncrementalRequest"]).IncrementalRequest(
            source="binance_spot",
            dataset="klines",
            symbol="BTCUSDT",
            interval="1h",
            bootstrap_start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2),
        )
    )

    assert result.start_date_used == date(2024, 1, 1)
    assert result.partitions_written == 2
    assert result.rows_written == 2
    assert result.watermark_before is None
    assert result.watermark_after is not None
    assert len(watermark_store.writes) == 1


def test_incremental_noops_when_watermark_is_after_end_date() -> None:
    from ingestion.pipeline import IncrementalRequest
    from ingestion.state.watermark import Watermark

    client = FakeClient()
    writer = FakeWriter()
    watermark_store = FakeWatermarkStore(
        Watermark(
            source="binance_spot",
            dataset="klines",
            symbol="BTCUSDT",
            interval="1h",
            last_open_time_ms=_utc_date_start_ms(date(2024, 1, 1)) + 23 * 3_600_000,
            updated_at=datetime(2024, 1, 2),
        )
    )

    pipeline = IngestionPipeline(
        client=client,
        writer=writer,
        watermark_store=watermark_store,
    )

    result = pipeline.run_incremental(
        IncrementalRequest(
            source="binance_spot",
            dataset="klines",
            symbol="BTCUSDT",
            interval="1h",
            bootstrap_start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
        )
    )

    assert result.start_date_used == date(2024, 1, 2)
    assert result.partitions_written == 0
    assert result.rows_written == 0
    assert len(client.calls) == 0
    assert len(writer.calls) == 0
    assert len(watermark_store.writes) == 0
