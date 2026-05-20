from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from ingestion.models import Kline
from ingestion.storage.gcs_raw import GCSRawWriter, RawPartitionSpec

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


class FakeBlob:
    def __init__(self, name: str, writes: list[dict[str, Any]]) -> None:
        self.name = name
        self.writes = writes

    def upload_from_filename(self, filename: str, content_type: str | None = None) -> None:
        import pyarrow.parquet as pq

        self.writes.append(
            {
                "blob_name": self.name,
                "filename": filename,
                "content_type": content_type,
                "size_bytes": Path(filename).stat().st_size,
                "parquet_schema": str(pq.read_schema(filename)),
            }
        )


class FakeBucket:
    def __init__(self, writes: list[dict[str, Any]]) -> None:
        self.writes = writes

    def blob(self, blob_name: str) -> FakeBlob:
        return FakeBlob(name=blob_name, writes=self.writes)


class FakeStorageClient:
    def __init__(self) -> None:
        self.writes: list[dict[str, Any]] = []

    def bucket(self, bucket_name: str) -> FakeBucket:
        return FakeBucket(writes=self.writes)


def make_kline(open_time_ms: int = 1704067200000) -> Kline:
    row = SAMPLE_KLINE.copy()
    row[0] = open_time_ms
    row[6] = open_time_ms + 3_599_999
    return Kline.from_binance_row(row)


def test_writer_uses_same_object_path_for_same_partition(tmp_path: Path) -> None:
    client = FakeStorageClient()
    writer = GCSRawWriter(
        bucket_name="test-raw-bucket",
        client=client,
        temp_dir=tmp_path,
    )
    spec = RawPartitionSpec(
        source="binance_spot",
        dataset="klines",
        symbol="BTCUSDT",
        interval="1h",
        partition_date=date(2024, 1, 1),
    )

    loaded_at = datetime(2024, 1, 2, tzinfo=UTC)

    first = writer.write_klines_partition(
        rows=[make_kline()],
        spec=spec,
        loaded_at=loaded_at,
        batch_id="batch-001",
    )
    second = writer.write_klines_partition(
        rows=[make_kline()],
        spec=spec,
        loaded_at=loaded_at,
        batch_id="batch-001",
    )

    assert first.object_path == second.object_path
    assert first.gcs_uri == second.gcs_uri
    assert len(client.writes) == 2
    assert client.writes[0]["blob_name"] == client.writes[1]["blob_name"]
    assert client.writes[0]["size_bytes"] > 0


def test_writer_rejects_duplicate_natural_keys(tmp_path: Path) -> None:
    client = FakeStorageClient()
    writer = GCSRawWriter(
        bucket_name="test-raw-bucket",
        client=client,
        temp_dir=tmp_path,
    )
    spec = RawPartitionSpec(
        source="binance_spot",
        dataset="klines",
        symbol="BTCUSDT",
        interval="1h",
        partition_date=date(2024, 1, 1),
    )

    duplicate = make_kline()

    with pytest.raises(ValueError, match="Duplicate open_time_ms"):
        writer.write_klines_partition(
            rows=[duplicate, duplicate],
            spec=spec,
        )


def test_writer_rejects_rows_outside_partition_date(tmp_path: Path) -> None:
    client = FakeStorageClient()
    writer = GCSRawWriter(
        bucket_name="test-raw-bucket",
        client=client,
        temp_dir=tmp_path,
    )
    spec = RawPartitionSpec(
        source="binance_spot",
        dataset="klines",
        symbol="BTCUSDT",
        interval="1h",
        partition_date=date(2024, 1, 2),
    )

    with pytest.raises(ValueError, match="partition date"):
        writer.write_klines_partition(
            rows=[make_kline()],
            spec=spec,
        )


def test_writer_keeps_timestamp_fields_as_datetimes_for_bigquery() -> None:
    loaded_at = datetime(2024, 1, 2, tzinfo=UTC)
    spec = RawPartitionSpec(
        source="binance_spot",
        dataset="klines",
        symbol="BTCUSDT",
        interval="1h",
        partition_date=date(2024, 1, 1),
    )

    record = GCSRawWriter._kline_to_record(
        row=make_kline(),
        spec=spec,
        loaded_at=loaded_at,
        batch_id="batch-001",
    )

    assert isinstance(record["open_time_utc"], datetime)
    assert isinstance(record["close_time_utc"], datetime)
    assert isinstance(record["loaded_at"], datetime)
    assert record["open_time_utc"].tzinfo is not None
    assert record["close_time_utc"].tzinfo is not None
    assert record["loaded_at"].tzinfo is not None


def test_writer_parquet_timestamps_are_bigquery_compatible(tmp_path: Path) -> None:
    client = FakeStorageClient()
    writer = GCSRawWriter(
        bucket_name="test-raw-bucket",
        client=client,
        temp_dir=tmp_path,
    )
    spec = RawPartitionSpec(
        source="binance_spot",
        dataset="klines",
        symbol="BTCUSDT",
        interval="1h",
        partition_date=date(2024, 1, 1),
    )

    writer.write_klines_partition(
        rows=[make_kline()],
        spec=spec,
        loaded_at=datetime(2024, 1, 2, tzinfo=UTC),
        batch_id="batch-001",
    )

    parquet_schema = client.writes[0]["parquet_schema"]

    assert "open_time_utc: timestamp[us" in parquet_schema
    assert "close_time_utc: timestamp[us" in parquet_schema
    assert "loaded_at: timestamp[us" in parquet_schema
