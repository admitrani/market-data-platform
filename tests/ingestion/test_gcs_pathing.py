from __future__ import annotations

from datetime import date

from ingestion.storage.gcs_raw import RawPartitionSpec


def test_raw_partition_spec_builds_deterministic_object_path() -> None:
    spec = RawPartitionSpec(
        source="binance_spot",
        dataset="klines",
        symbol="BTCUSDT",
        interval="1h",
        partition_date=date(2024, 1, 1),
    )

    assert (
        spec.object_path == "raw/source=binance_spot/"
        "dataset=klines/"
        "symbol=BTCUSDT/"
        "interval=1h/"
        "date=2024-01-01/"
        "data.parquet"
    )
