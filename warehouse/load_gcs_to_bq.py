"""Load raw GCS Parquet partitions into BigQuery raw tables."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from google.cloud import bigquery


class BigQueryClientLike(Protocol):
    def load_table_from_uri(
        self,
        source_uris: str | list[str],
        destination: str,
        job_config: bigquery.LoadJobConfig,
    ): ...


@dataclass(frozen=True)
class RawKlinesLoadConfig:
    """Configuration for loading raw kline Parquet files into BigQuery."""

    project_id: str
    dataset_id: str
    table_id: str
    gcs_uri: str

    @property
    def destination_table(self) -> str:
        return f"{self.project_id}.{self.dataset_id}.{self.table_id}"


RAW_KLINES_SCHEMA = [
    bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("dataset", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("symbol", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("interval", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("open_time_ms", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("open_time_utc", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("open", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("high", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("low", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("close", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("volume", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("close_time_ms", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("close_time_utc", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("quote_asset_volume", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("number_of_trades", "INT64", mode="REQUIRED"),
    bigquery.SchemaField("taker_buy_base_asset_volume", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("taker_buy_quote_asset_volume", "FLOAT64", mode="REQUIRED"),
    bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("batch_id", "STRING", mode="REQUIRED"),
]


def build_raw_klines_load_job_config() -> bigquery.LoadJobConfig:
    """Build a cost-safe BigQuery load job config for raw klines."""

    return bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        schema=RAW_KLINES_SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        time_partitioning=bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="open_time_utc",
        ),
        clustering_fields=["symbol", "interval"],
    )


def load_raw_klines_from_gcs(
    config: RawKlinesLoadConfig,
    client: BigQueryClientLike | None = None,
) -> str:
    """Load raw klines from GCS Parquet into a partitioned BigQuery table.

    WRITE_TRUNCATE is intentional for Phase 2 walking skeleton:
    the raw table is rebuilt from the current GCS raw slice deterministically.
    Later orchestration can switch to partition-level incremental loads.
    """

    bq_client = client or bigquery.Client(project=config.project_id)
    job_config = build_raw_klines_load_job_config()

    load_job = bq_client.load_table_from_uri(
        source_uris=config.gcs_uri,
        destination=config.destination_table,
        job_config=job_config,
    )

    load_job.result()

    return config.destination_table
