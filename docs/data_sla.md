# Data SLA

## Objective

This document defines the expected data availability, freshness, quality, and cost-control checks for the Market Data Platform.

The current project is a development and portfolio environment, not a production trading feed.

## Dataset Scope

Current asset:

```text
BTCUSDT
```

Current interval:

```
1h
```

Primary warehouse marts:

- marts.fact_prices
- marts.fact_price_features
- marts.dashboard_price_timeseries
- marts.dashboard_daily_summary
- marts.dashboard_data_status

## Freshness Definitions

The platform distinguishes between two timestamps:

### Market freshness

```
latest_market_bar_utc
```

The latest actual market timestamp present in the dataset.

### Load freshness

```
latest_loaded_at
```

The latest pipeline load timestamp.

This distinction matters because historical market data can be loaded recently while the underlying market bars are older.

## SLA Targets

For a future scheduled production-style pipeline:

Metric - Target
- Raw ingestion freshness - less than 24 hours behind schedule
- Mart refresh freshness - less than 24 hours behind raw
- 1h bar daily completeness - 24 bars per UTC day
- dbt source freshness warning - 7 days
- dbt source freshness error - 30 days
- BigQuery CI byte limit - 31,457,280 bytes per query

For the current development dataset, the SLA is evaluated as a historical sample/backfill rather than a live feed.

## Quality Checks

The platform validates:

- non-null key market fields
- unique natural keys
- OHLC consistency
- no negative volume
- no hourly gaps in mart facts
- relationship integrity between facts and dimensions
- rolling-window completeness for feature views

## Observability Commands

Run source freshness:

```bash
make dbt-source-freshness PROJECT_ID="$(gcloud config get-value project)" BQ_MAX_BYTES=31457280
```

Run all observability checks:

```bash
make observability PROJECT_ID="$(gcloud config get-value project)" BQ_MAX_BYTES=31457280
```

Run individual checks:

```bash
make observability-status PROJECT_ID="$(gcloud config get-value project)" BQ_MAX_BYTES=31457280
make observability-cost PROJECT_ID="$(gcloud config get-value project)" BQ_MAX_BYTES=31457280
make observability-coverage PROJECT_ID="$(gcloud config get-value project)" BQ_MAX_BYTES=31457280
```

## Cost Guardrails

The project is designed to stay within a GCP free plan / free trial budget.

Controls:

- no always-on compute services
- no Cloud Composer
- no automatic Terraform apply in CI
- BigQuery queries use maximum_bytes_billed
- dbt CI writes to isolated ci dataset
- cloud-touching workflows are manual or path-scoped
- branch protection requires cloud-safe quality checks before merge

## Incident Response

If freshness or coverage checks fail:

1. Check the latest raw partitions in GCS.
2. Check raw.raw_klines row counts and latest loaded_at.
3. Run make dbt-source-freshness.
4. Run make validate-raw.
5. Run make dbt-build.
6. Run make validate-marts.
7. Inspect Airflow DAG logs if orchestration was used.
8. Review BigQuery job history using make observability-cost.

## Known Limitations

- Current dataset is a historical sample/backfill.
- Current orchestration is local/Docker-based.
- No production alerting system is configured yet.
- No always-on scheduler is deployed to GCP to avoid unnecessary cost.
