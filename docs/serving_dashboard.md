# Serving Dashboard

## Objective

This dashboard is designed as a lightweight serving layer for demonstrating the Market Data Platform.

It uses curated BigQuery marts and dashboard-specific dbt serving views.

## Data Source

BigQuery project:

```text
market-data-platform-adam-dev
```

Dataset:

```
marts
```

Recommended dashboard views:

- dashboard_price_timeseries
- dashboard_daily_summary
- dashboard_data_status

## Current Demo Dataset Scope

The current dataset is a historical sample/backfill used for development and portfolio demonstration.

It should not be presented as a live production feed.

Key distinction:

- latest_market_bar_utc: latest market timestamp available in the dataset
- latest_loaded_at: latest pipeline load timestamp

This distinction is important because historical data may be loaded recently while the market timestamps themselves are older.

## Recommended Looker Studio Pages

### Page 1 — Market Overview

Scorecards:

- Latest market bar UTC
- Latest load timestamp
- Total bars
- Total market days
- Full 24h rolling-window ratio

Charts:

- BTCUSDT close price over time
- Hourly return over time
- 24h rolling volatility over time
- Volume over time

Primary table/view:

```
marts.dashboard_price_timeseries
```

### Page 2 — Daily Summary

Charts:

- Daily close price
- Daily return
- Daily volume
- Average rolling volatility by day

Primary table/view:

```
marts.dashboard_daily_summary
```

### Page 3 — Data Quality / Freshness

Scorecards:

- First market bar UTC
- Latest market bar UTC
- Latest loaded at
- Hours since latest market bar
- Hours since latest load
- Full 24h rolling-window ratio

Primary table/view:

```
marts.dashboard_data_status
```

This dashboard sits on top of the dbt mart layer.

The ingestion pipeline lands raw market data in GCS and BigQuery raw. dbt then transforms the raw data into staging, intermediate, and mart models with tests, documentation, and CI validation.

The dashboard uses a separate serving layer so that business-facing reporting does not directly depend on lower-level transformation models.

The project is cost-controlled for a GCP free plan through BigQuery byte limits, manual cloud-touching workflows, and branch protection.

## Looker Studio Report

Dashboard URL:

```text
https://datastudio.google.com/reporting/f5658838-b5e3-4daa-967c-eedb8a17abdd/page/1HtyF
```

Access mode:

```
Restricted during development. Can be changed to link-view access for portfolio sharing.
```
