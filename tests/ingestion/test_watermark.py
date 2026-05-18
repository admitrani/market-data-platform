from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ingestion.state.watermark import GCSWatermarkStore, Watermark


class FakeBlob:
    def __init__(self, name: str, objects: dict[str, str]) -> None:
        self.name = name
        self.objects = objects

    def exists(self) -> bool:
        return self.name in self.objects

    def download_as_text(self) -> str:
        return self.objects[self.name]

    def upload_from_string(self, data: str, content_type: str | None = None) -> None:
        self.objects[self.name] = data


class FakeBucket:
    def __init__(self, objects: dict[str, str]) -> None:
        self.objects = objects

    def blob(self, blob_name: str) -> FakeBlob:
        return FakeBlob(name=blob_name, objects=self.objects)


class FakeStorageClient:
    def __init__(self) -> None:
        self.objects: dict[str, str] = {}

    def bucket(self, bucket_name: str) -> FakeBucket:
        return FakeBucket(objects=self.objects)


def test_watermark_path_is_deterministic() -> None:
    path = GCSWatermarkStore.object_path(
        source="binance_spot",
        dataset="klines",
        symbol="BTCUSDT",
        interval="1h",
    )

    assert (
        path
        == "state/watermarks/source=binance_spot/"
        "dataset=klines/"
        "symbol=BTCUSDT/"
        "interval=1h/"
        "watermark.json"
    )


def test_read_missing_watermark_returns_none() -> None:
    client = FakeStorageClient()
    store = GCSWatermarkStore(bucket_name="test-bucket", client=client)

    watermark = store.read(
        source="binance_spot",
        dataset="klines",
        symbol="BTCUSDT",
        interval="1h",
    )

    assert watermark is None


def test_write_and_read_watermark_roundtrip() -> None:
    client = FakeStorageClient()
    store = GCSWatermarkStore(bucket_name="test-bucket", client=client)

    original = Watermark(
        source="binance_spot",
        dataset="klines",
        symbol="BTCUSDT",
        interval="1h",
        last_open_time_ms=1704150000000,
        updated_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )

    store.write(original)

    loaded = store.read(
        source="binance_spot",
        dataset="klines",
        symbol="BTCUSDT",
        interval="1h",
    )

    assert loaded == original
