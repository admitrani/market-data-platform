"""GCS raw-zone writer for partitioned Parquet market data."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Protocol, Sequence
from uuid import uuid4

import pandas as pd
from google.cloud import storage

from ingestion.models import Kline


class BlobLike(Protocol):
    def upload_from_filename(self, filename: str, content_type: str | None = None) -> None:
        ...


class BucketLike(Protocol):
    def blob(self, blob_name: str) -> BlobLike:
        ...


class StorageClientLike(Protocol):
    def bucket(self, bucket_name: str) -> BucketLike:
        ...


@dataclass(frozen=True)
class RawPartitionSpec:
    """Deterministic GCS raw partition specification."""

    source: str
    dataset: str
    symbol: str
    interval: str
    partition_date: date

    @property
    def object_path(self) -> str:
        return (
            f"raw/source={self.source}/"
            f"dataset={self.dataset}/"
            f"symbol={self.symbol}/"
            f"interval={self.interval}/"
            f"date={self.partition_date.isoformat()}/"
            "data.parquet"
        )


@dataclass(frozen=True)
class GCSWriteResult:
    """Metadata returned after writing one raw partition."""

    bucket_name: str
    object_path: str
    row_count: int
    min_open_time_ms: int
    max_open_time_ms: int

    @property
    def gcs_uri(self) -> str:
        return f"gs://{self.bucket_name}/{self.object_path}"


class GCSRawWriter:
    """Writes validated market data rows to deterministic GCS Parquet paths."""

    def __init__(
        self,
        bucket_name: str,
        client: StorageClientLike | None = None,
        temp_dir: str | Path | None = None,
    ) -> None:
        self.bucket_name = bucket_name
        self.client = client or storage.Client()
        self.temp_dir = Path(temp_dir) if temp_dir else None

    def write_klines_partition(
        self,
        rows: Sequence[Kline],
        spec: RawPartitionSpec,
        loaded_at: datetime | None = None,
        batch_id: str | None = None,
    ) -> GCSWriteResult:
        """Write one date partition to GCS as Parquet.

        Idempotency strategy:
        - object path is deterministic
        - same source/dataset/symbol/interval/date writes to the same object
        - rerunning the same partition overwrites the same Parquet object, not a new file
        """

        if not rows:
            raise ValueError("Cannot write an empty raw partition")

        self._validate_partition_rows(rows=rows, spec=spec)

        loaded_at = loaded_at or datetime.now(timezone.utc)
        batch_id = batch_id or str(uuid4())

        records = [
            self._kline_to_record(
                row=row,
                spec=spec,
                loaded_at=loaded_at,
                batch_id=batch_id,
            )
            for row in sorted(rows, key=lambda item: item.open_time_ms)
        ]

        df = pd.DataFrame.from_records(records)

        with tempfile.NamedTemporaryFile(
            suffix=".parquet",
            dir=self.temp_dir,
            delete=True,
        ) as tmp_file:
            df.to_parquet(tmp_file.name, index=False)

            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(spec.object_path)
            blob.upload_from_filename(
                tmp_file.name,
                content_type="application/octet-stream",
            )

        return GCSWriteResult(
            bucket_name=self.bucket_name,
            object_path=spec.object_path,
            row_count=len(rows),
            min_open_time_ms=min(row.open_time_ms for row in rows),
            max_open_time_ms=max(row.open_time_ms for row in rows),
        )

    @staticmethod
    def _validate_partition_rows(rows: Sequence[Kline], spec: RawPartitionSpec) -> None:
        open_times = [row.open_time_ms for row in rows]

        if len(open_times) != len(set(open_times)):
            raise ValueError("Duplicate open_time_ms found in raw partition")

        for row in rows:
            row_date = row.open_datetime_utc.date()
            if row_date != spec.partition_date:
                raise ValueError(
                    "All rows in one raw partition must belong to the partition date. "
                    f"Expected {spec.partition_date.isoformat()}, got {row_date.isoformat()}."
                )

    @staticmethod
    def _kline_to_record(
        row: Kline,
        spec: RawPartitionSpec,
        loaded_at: datetime,
        batch_id: str,
    ) -> dict[str, object]:
        return {
            "source": spec.source,
            "dataset": spec.dataset,
            "symbol": spec.symbol,
            "interval": spec.interval,
            "open_time_ms": row.open_time_ms,
            "open_time_utc": row.open_datetime_utc,
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
            "volume": row.volume,
            "close_time_ms": row.close_time_ms,
            "close_time_utc": row.close_datetime_utc,
            "quote_asset_volume": row.quote_asset_volume,
            "number_of_trades": row.number_of_trades,
            "taker_buy_base_asset_volume": row.taker_buy_base_asset_volume,
            "taker_buy_quote_asset_volume": row.taker_buy_quote_asset_volume,
            "loaded_at": loaded_at,
            "batch_id": batch_id,
        }
