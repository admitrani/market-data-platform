# Phase 3 — dbt Professional Layer

## Objective

Build a professional dbt transformation layer on top of the BigQuery raw market data table.

The pipeline now supports:

```text
GCS raw Parquet
  -> BigQuery raw.raw_klines
  -> dbt staging.stg_klines
  -> dbt intermediate.int_klines_normalized
  -> dbt marts.dim_symbol
  -> dbt marts.dim_calendar
  -> dbt marts.fact_prices
  -> dbt marts.fact_price_features
```

## Implemented layers

### Staging

Model:

- staging.stg_klines

Responsibilities:

- Rename raw fields into analytics-friendly names.
- Convert interval into bar_interval.
- Preserve ingestion metadata: loaded_at, batch_id.
- Enforce source-level quality tests.

Key tests:

- not null checks
- accepted values for source, dataset, symbol and interval
- OHLC consistency
- non-negative volume
- unique natural key validation

### Intermediate

Model:

- intermediate.int_klines_normalized

Responsibilities:

- Deduplicate records by natural key.
- Keep the latest loaded record per symbol, bar_interval, open_time_utc.
- Provide a stable normalized model for downstream marts.

### Marts

Models:

- marts.dim_symbol
- marts.dim_calendar
- marts.fact_prices
- marts.fact_price_features

Responsibilities:

- Provide a basic star schema for analytics.
- Use fact_prices as the canonical incremental fact table.
- Build fact_price_features as the analytical feature mart for reporting and future ML exploration.

## Incremental model

marts.fact_prices is materialized incrementally using merge semantics.

Natural key:

- symbol + bar_interval + open_time_utc

This prevents duplicate rows when the same time range is reprocessed.

## Cost controls

BigQuery cost is controlled using:

- partitioning by open_time_utc
- clustering by symbol and bar_interval
- maximum_bytes_billed in dbt profile
- dry-run checks for query estimates
- small development dataset for early validation


## Data quality checks

The dbt layer includes tests for:

- source freshness
- accepted values
- not-null constraints
- relationship integrity between facts and dimensions
- natural key uniqueness
- hourly gap detection
- OHLC consistency
- non-negative volume
- feature range sanity checks
- first-return null behavior
- log-return consistency

## Current validation state

Latest validated state:

- dbt build: PASS
- fact_prices rows: 120
- fact_price_features rows: 120
- symbol: BTCUSDT
- bar_interval: 1h
- date range: 2024-01-01 00:00:00 to 2024-01-05 23:00:00

## Portfolio explanation

This phase demonstrates a production-style analytics engineering workflow:

- raw-to-staging-to-mart dbt structure
- BigQuery warehouse modeling
- star schema design
- incremental fact table
- source freshness checks
- data quality tests
- lineage documentation
- cost-aware cloud usage
