# Source Freshness Runbook

## Command

```bash
make dbt-source-freshness PROJECT_ID="$(gcloud config get-value project)" BQ_MAX_BYTES=31457280
```

## Source

dbt source:

```
raw.raw_klines
```

## Current thresholds

Defined in:

```
dbt/models/staging/schema.yml
```

Current freshness policy:

- warning after 7 days
- error after 30 days

## Interpretation

dbt source freshness checks the raw table loaded_at field.

This should be interpreted together with mart-level market timestamps:

- latest_loaded_at: when the pipeline loaded the data
- latest_market_bar_utc: latest actual market timestamp in the dataset

For historical backfills, latest_loaded_at can be recent while latest_market_bar_utc is old.
