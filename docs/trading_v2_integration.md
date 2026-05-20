# Trading v2 Integration Contract

## Objective

This document describes how the Market Data Platform can serve curated market data to a downstream trading or ML research system.

The current goal is not to tightly couple repositories. The goal is to define a clear contract between:

```text
Market Data Platform → trusted BigQuery serving layer → Trading v2 research system
```

## Recommended Source for Trading v2

Primary serving view:

```
marts.dashboard_price_timeseries
```

This view is built on top of:

```
marts.fact_price_features
```

It exposes BTCUSDT 1h OHLCV data and basic engineered features.

## Current Dataset Scope

Current asset:

```
BTCUSDT
```

Current interval:

```
1h
```

The current dataset is a historical development/backfill sample, not a live trading feed.

- open_time_utc is the actual market bar timestamp.
- loaded_at is when the pipeline loaded the data.

Historical data can be loaded recently while still containing older market timestamps.

## Candidate Feature Columns

Core market fields:

- open_time_utc
- open
- high
- low
- close
- volume

Microstructure / exchange activity fields:

- quote_asset_volume
- number_of_trades
- taker_buy_base_asset_volume
- taker_buy_quote_asset_volume

Basic engineered features:

- return_1h
- log_return_1h
- price_range
- price_range_pct
- body_size_pct
- volume_change_1h
- rolling_mean_close_24h
- rolling_volatility_24h
- rolling_volume_mean_24h
- rolling_window_observations_24h

## Data Contract Guarantees

The platform validates:

- non-null key market fields
- unique timestamps at the expected grain
- OHLC consistency
- no negative volume
- no hourly gaps in mart facts
- relationship integrity between fact and dimension tables
- rolling-window completeness for feature rows

The downstream trading system should treat this serving view as a trusted but still research-stage source.

## Example BigQuery Extraction Query

Query file:

```
warehouse/consumption/trading_v2_feature_extract.sql
```

Purpose:

```
Extract chronological BTCUSDT 1h feature rows for downstream model research.
```

## Example Data Contract Check

Query file:

```
warehouse/consumption/trading_v2_data_contract_check.sql
```

Purpose:

```
Validate row counts, date coverage, null counts, and rolling-window completeness before consuming the data.
```

## Recommended Integration Pattern

For the next project stage:

1. Trading v2 reads from BigQuery using a read-only service account.
2. Data is pulled into a local research environment as Parquet.
3. A dataset snapshot is versioned by:
    - source table/view name
    - extraction timestamp
    - min/max open_time_utc
    - row count
    - Git commit of this repo
4. Trading v2 freezes the extracted dataset before feature engineering or model selection.

## Anti-Leakage Considerations

This platform currently exposes historical features only.

Downstream trading v2 must still enforce:

- no future-looking labels in the feature table
- point-in-time splits
- walk-forward validation
- no use of holdout data during research
- feature/label alignment checks

The Market Data Platform provides clean market data and basic features. It does not replace trading-specific validation.

## Production Extensions

At production scale, this integration could be extended with:

- dedicated BigQuery authorized views
- a read-only consumer service account
- scheduled exports to GCS Parquet
- partitioned dataset snapshots
- data contracts with schema versioning
- Great Expectations or dbt exposures
- alerting when freshness or coverage SLAs fail


This repo produces trusted, tested market-data marts. My trading v2 system should not scrape raw exchange data directly. Instead, it should consume a stable serving contract from the data platform.

That separation lets me reason about data quality, lineage, reproducibility, and cost independently from model research.
