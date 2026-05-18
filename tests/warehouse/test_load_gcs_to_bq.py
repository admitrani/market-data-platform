from __future__ import annotations

from typing import Any

from google.cloud import bigquery

from warehouse.load_gcs_to_bq import (
    RawKlinesLoadConfig,
    build_raw_klines_load_job_config,
    load_raw_klines_from_gcs,
)


class FakeLoadJob:
    def __init__(self) -> None:
        self.result_called = False

    def result(self) -> None:
        self.result_called = True


class FakeBigQueryClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.job = FakeLoadJob()

    def load_table_from_uri(
        self,
        source_uris: str | list[str],
        destination: str,
        job_config: bigquery.LoadJobConfig,
    ) -> FakeLoadJob:
        self.calls.append(
            {
                "source_uris": source_uris,
                "destination": destination,
                "job_config": job_config,
            }
        )
        return self.job


def test_raw_load_config_destination_table() -> None:
    config = RawKlinesLoadConfig(
        project_id="test-project",
        dataset_id="raw",
        table_id="raw_klines",
        gcs_uri="gs://bucket/raw/*.parquet",
    )

    assert config.destination_table == "test-project.raw.raw_klines"


def test_build_raw_klines_load_job_config() -> None:
    job_config = build_raw_klines_load_job_config()

    assert job_config.source_format == bigquery.SourceFormat.PARQUET
    assert job_config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE
    assert job_config.time_partitioning.field == "open_time_utc"
    assert job_config.clustering_fields == ["symbol", "interval"]

    schema_names = [field.name for field in job_config.schema]
    assert "symbol" in schema_names
    assert "open_time_utc" in schema_names
    assert "loaded_at" in schema_names
    assert "batch_id" in schema_names


def test_load_raw_klines_from_gcs_starts_load_job() -> None:
    fake_client = FakeBigQueryClient()
    config = RawKlinesLoadConfig(
        project_id="test-project",
        dataset_id="raw",
        table_id="raw_klines",
        gcs_uri="gs://bucket/raw/source=binance_spot/dataset=klines/**/*.parquet",
    )

    destination = load_raw_klines_from_gcs(config=config, client=fake_client)

    assert destination == "test-project.raw.raw_klines"
    assert len(fake_client.calls) == 1
    assert fake_client.calls[0]["source_uris"] == config.gcs_uri
    assert fake_client.calls[0]["destination"] == "test-project.raw.raw_klines"
    assert fake_client.job.result_called is True
