"""GCS-backed ingestion watermarks."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Protocol

from google.cloud import storage


class BlobLike(Protocol):
    def exists(self) -> bool: ...

    def download_as_text(self) -> str: ...

    def upload_from_string(self, data: str, content_type: str | None = None) -> None: ...


class BucketLike(Protocol):
    def blob(self, blob_name: str) -> BlobLike: ...


class StorageClientLike(Protocol):
    def bucket(self, bucket_name: str) -> BucketLike: ...


@dataclass(frozen=True)
class Watermark:
    """Latest successfully written market-data position."""

    source: str
    dataset: str
    symbol: str
    interval: str
    last_open_time_ms: int
    updated_at: datetime

    def to_json(self) -> str:
        payload = asdict(self)
        payload["updated_at"] = self.updated_at.isoformat()
        return json.dumps(payload, indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> Watermark:
        payload = json.loads(raw)
        return cls(
            source=payload["source"],
            dataset=payload["dataset"],
            symbol=payload["symbol"],
            interval=payload["interval"],
            last_open_time_ms=int(payload["last_open_time_ms"]),
            updated_at=datetime.fromisoformat(payload["updated_at"]),
        )


class GCSWatermarkStore:
    """Reads and writes ingestion watermarks in GCS."""

    def __init__(
        self,
        bucket_name: str,
        client: StorageClientLike | None = None,
    ) -> None:
        self.bucket_name = bucket_name
        self.client = client or storage.Client()

    @staticmethod
    def object_path(
        *,
        source: str,
        dataset: str,
        symbol: str,
        interval: str,
    ) -> str:
        return (
            f"state/watermarks/source={source}/"
            f"dataset={dataset}/"
            f"symbol={symbol}/"
            f"interval={interval}/"
            "watermark.json"
        )

    def read(
        self,
        *,
        source: str,
        dataset: str,
        symbol: str,
        interval: str,
    ) -> Watermark | None:
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(
            self.object_path(
                source=source,
                dataset=dataset,
                symbol=symbol,
                interval=interval,
            )
        )

        if not blob.exists():
            return None

        return Watermark.from_json(blob.download_as_text())

    def write(self, watermark: Watermark) -> None:
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(
            self.object_path(
                source=watermark.source,
                dataset=watermark.dataset,
                symbol=watermark.symbol,
                interval=watermark.interval,
            )
        )
        blob.upload_from_string(
            watermark.to_json(),
            content_type="application/json",
        )


def new_watermark(
    *,
    source: str,
    dataset: str,
    symbol: str,
    interval: str,
    last_open_time_ms: int,
) -> Watermark:
    return Watermark(
        source=source,
        dataset=dataset,
        symbol=symbol,
        interval=interval,
        last_open_time_ms=last_open_time_ms,
        updated_at=datetime.now(UTC),
    )
