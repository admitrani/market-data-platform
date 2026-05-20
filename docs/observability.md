# Observability

## Purpose

The observability layer provides lightweight operational visibility into the Market Data Platform without deploying additional cloud services.

It focuses on:

- source freshness
- mart coverage
- dashboard data status
- BigQuery usage and cost
- dbt documentation and tests

## Components

### dbt Source Freshness

Command:

```bash
make dbt-source-freshness PROJECT_ID="$(gcloud config get-value project)" BQ_MAX_BYTES=31457280
```

Configured in:

```
dbt/models/staging/schema.yml
```

### Data Status View

Model:

```
marts.dashboard_data_status
```

Tracks:

- total bars
- total market days
- first market timestamp
- latest market timestamp
- latest load timestamp
- hours since latest market bar
- hours since latest load
- rolling 24h window completeness

### BigQuery Usage Query

Query file:

```
warehouse/observability/bigquery_usage_last_7_days.sql
```

Command:

```bash
make observability-cost PROJECT_ID="$(gcloud config get-value project)" BQ_MAX_BYTES=31457280
```

### Data Coverage Query

Query file:

```
warehouse/observability/data_coverage_by_day.sql
```

Command:

```bash
make observability-coverage PROJECT_ID="$(gcloud config get-value project)" BQ_MAX_BYTES=31457280
```

## Demo Interpretation

For interview or portfolio demos, explain:

1. Data lands in GCS and BigQuery raw.
2. dbt transforms raw data into staging, intermediate and mart layers.
3. dbt tests validate schema, uniqueness, relationships, and market-data rules.
4. The dashboard serving layer exposes clean reporting views.
5. Observability checks verify freshness, coverage, and BigQuery cost.
6. CI/CD prevents broken changes from reaching main.

## No Always-On Monitoring

This project intentionally avoids always-on monitoring infrastructure to stay within the GCP free plan / free trial cost guardrails.

At production scale, this would be extended with:

- scheduled orchestration
- alerting
- persisted observability tables
- monitoring dashboards
- incident notification channels
