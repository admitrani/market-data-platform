# Phase 4 — Orchestration

## Objective

Build a reproducible orchestration layer for the Market Data Platform.

The current orchestration stack is intentionally local-first and cost-controlled:

```text
Makefile
  -> reproducible command interface

Local Airflow
  -> scheduling, dependencies, retries and observability

GCP
  -> only storage and warehouse resources already provisioned
```

Cloud Composer is intentionally not used in this phase because it introduces non-trivial always-on managed-service cost. The project demonstrates Airflow orchestration locally while keeping the cloud footprint minimal.

## Runtime environments

The project uses two separate virtual environments:

.venv
  Project runtime:
  - ingestion code
  - pytest
  - dbt
  - Google Cloud clients

.venv-airflow
  Airflow runtime only:
  - apache-airflow
  - Airflow metadata DB
  - local DAG execution

This separation prevents Airflow dependency constraints from breaking dbt or ingestion dependencies.

## Command interface

The Makefile is the canonical command interface.

Core targets:

```bash
make check-env
make test
make ingest-backfill
make ingest-incremental
make load-bq-raw
make dbt-build
make dbt-docs
make validate-raw
make validate-marts
make cost-check
make phase4-dev
```

The local Airflow DAG orchestrates these Makefile targets instead of duplicating business logic inside the DAG.

## Local pipeline flow

The current development pipeline is:

check-env
  - test
  - ingest-backfill
  - load-bq-raw
  - dbt-build
  - validate-raw
  - validate-marts
  - cost-check

The equivalent one-command local run is:

- make phase4-dev

The equivalent Airflow run is:

```bash
source .venv-airflow/bin/activate

export AIRFLOW_HOME="$PWD/.airflow_home"
export AIRFLOW__CORE__DAGS_FOLDER="$PWD/orchestration/airflow/dags"
export AIRFLOW__CORE__LOAD_EXAMPLES=False

airflow dags test market_data_platform_dev 2024-01-02
```

### Airflow DAG

DAG path:

- orchestration/airflow/dags/market_data_platform_dev.py

DAG id:

- market_data_platform_dev

The DAG runs in .venv-airflow, but each BashOperator activates .venv before executing the project command:

```bash
. .venv/bin/activate && make <target>
```

This keeps Airflow isolated from the project runtime.

## Current validated state

Latest validated local Airflow run:

```
DAG: market_data_platform_dev
State: success

check_env: success
test: 23 passed
ingest_backfill: 5 partitions / 120 rows
load_bq_raw: success
dbt_build: PASS=79 WARN=0 ERROR=0
validate_raw: 120 rows
validate_marts: 120 rows, 119 returns, 97 complete 24h windows
cost_check: below BigQuery free tier
```

## Cost controls

The orchestration layer uses the same cost controls as the dbt and BigQuery layers:

BQ_MAX_BYTES=52428800

This caps manual and orchestration-triggered BigQuery queries at 50 MiB per query.

The cost-check target queries BigQuery job metadata and reports:

```
query_jobs
processed_mib
billed_mib
billed_tib
```

This should be checked after full pipeline runs.

## Why local Airflow instead of Cloud Composer

Cloud Composer is not used in the current phase because it can create recurring managed-service costs.

The project currently demonstrates:

- Airflow DAG design
- task dependencies
- BashOperator orchestration
- retries/failure behavior
- local metadata DB
- reproducible Makefile integration

This is sufficient for portfolio and interview purposes without paying for managed Airflow infrastructure.

## Runbook

### Problem: Airflow cannot find the DAG

Symptoms:

Dag 'market_data_platform_dev' could not be found

Checks:

```
ls -la orchestration/airflow/dags
airflow dags list-import-errors
airflow dags list | grep market
```

Expected file:

orchestration/airflow/dags/market_data_platform_dev.py

### Problem: PROJECT_ID is empty inside Airflow

Symptoms:

PROJECT_ID is empty. Run: gcloud config set project <project-id>

Cause:

Airflow BashOperator may not inherit the same shell environment as the terminal.

Fix:

The DAG explicitly passes these environment variables:

```
PROJECT_ID
RAW_BUCKET
BQ_LOCATION
BQ_MAX_BYTES
```

### Problem: Airflow breaks dbt dependencies

Symptoms:

```
pip check
dbt-core dependency conflicts
```

Cause:

Airflow constraints were installed into .venv.

Fix:

Keep environments separate:

```
.venv         -> project/dbt
.venv-airflow -> Airflow only
```

If .venv is polluted, recreate it and reinstall project dependencies.

### Problem: BigQuery query exceeds bytes billed limit

Symptoms:

Query exceeded limit for bytes billed

Fix:

Do not remove the limit blindly. First run a dry-run or inspect the query. If the increase is justified, raise BQ_MAX_BYTES gradually.

### Problem: dbt docs catalog fails on bytes limit

Symptoms:

```
dbt docs generate
Query exceeded limit for bytes billed
```

Fix:

Raise maximum_bytes_billed in dbt/profiles.yml only to the minimum required value.

## Portfolio explanation

This phase demonstrates a production-style orchestration pattern:

- Makefile as stable command interface
- Airflow as orchestration layer
- isolated runtime environments
- dbt build integrated into orchestration
- ingestion and warehouse loading controlled from a DAG
- validation and cost checks as first-class tasks
- local-first implementation to avoid unnecessary cloud costs

## Centralized pipeline configuration

The development pipeline configuration lives in:

```text
config/pipeline_dev.env
```

This file defines:

```text
PROJECT_ID
RAW_BUCKET
BQ_LOCATION
SYMBOL
INTERVAL
START_DATE
END_DATE
BQ_MAX_BYTES
```

Both the Makefile and the local Airflow DAG read from this config file.

This avoids duplicating runtime parameters and makes the local orchestration layer easier to change safely.

Example:

```bash
make phase4-dev
```

and:

```bash
airflow dags test market_data_platform_dev 2024-01-03
```

use the same project, bucket, symbol, interval, date range and BigQuery byte limit.

## Airflow Makefile targets

Airflow can also be controlled through Makefile targets:

```bash
make airflow-check
make airflow-db-migrate
make airflow-dag-list
make airflow-dag-test
```

These targets use:

```
.venv-airflow/bin/airflow
```

while the DAG tasks themselves activate:

```
.venv
```

before running the project pipeline commands.

This keeps orchestration and project runtime dependencies isolated while preserving a single command interface for local development.

## Production-shaped DAG

The Airflow DAG now separates dbt execution into distinct tasks:

```text
dbt_run
  -> dbt_test
  -> dbt_source_freshness
```

This is more production-like than calling dbt build as a single opaque step because the Airflow UI can show whether the failure came from:

- model execution
- data tests
- source freshness

The DAG flow is:

```
check_env
  -> unit_tests
  -> extract_load_gcs
  -> load_bq_raw
  -> dbt_run
  -> dbt_test
  -> dbt_source_freshness
  -> validate_raw / validate_marts
  -> cost_check
```

## Reliability policy

The Airflow DAG includes an explicit reliability layer:

```text
retries
retry_delay
retry_exponential_backoff
execution_timeout
dagrun_timeout
SLA policy
optional failure callback
```

The policy is configured in:

```
config/pipeline_dev.env
```

Current development defaults:

```
AIRFLOW_RETRIES=1
AIRFLOW_RETRY_DELAY_MINUTES=2
AIRFLOW_TASK_TIMEOUT_MINUTES=20
AIRFLOW_DAG_TIMEOUT_MINUTES=45
AIRFLOW_SLA_MINUTES=30
```

Task-specific timeouts are set in the DAG for critical steps such as ingestion, BigQuery loading, dbt run, dbt test, source freshness and validation.

## Failure alerting

The DAG defines an optional failure callback.

If SLACK_WEBHOOK_URL is available in the Airflow runtime environment, failed tasks send a Slack message containing:

```
dag_id
task_id
run_id
execution_date
try_number
exception
log_url
```

If SLACK_WEBHOOK_URL is not set, the callback logs the same payload to stdout. This keeps the project safe for Git while still demonstrating production-style failure notification design.

No Slack secrets are committed to the repository.

## Backfill and incremental recovery policy

The mart layer includes incremental models. A normal daily scheduled run can use:

```text
dbt-run
```

However, if a historical date is loaded after a later date already exists in the incremental mart, the incremental filter may skip the older backfilled rows.

The data-quality test assert_fact_prices_no_hourly_gaps is expected to catch this situation.

For controlled historical backfills, the DAG supports:

```json
{
  "start_date": "2024-01-08",
  "end_date": "2024-01-10",
  "full_refresh": true
}
```

When full_refresh=true, the DAG executes:

```
dbt-run-full-refresh
```

instead of:

```
dbt-run
```

This rebuilds the marts from raw data and removes gaps created by out-of-order historical loads.

This behavior was validated after an intentional out-of-order run caused assert_fact_prices_no_hourly_gaps to fail. Running dbt-run-full-refresh rebuilt the mart to 168 continuous hourly rows from 2024-01-01 00:00:00 to 2024-01-07 23:00:00, and all 72 dbt tests passed.

## Phase 4 closeout

### Final architecture

Phase 4 implements a local-first orchestration layer with:

```text
Docker Compose
  -> Postgres metadata DB
  -> Airflow webserver
  -> Airflow scheduler
  -> Airflow DAG
  -> Makefile command interface
  -> GCS raw ingestion
  -> BigQuery raw load
  -> dbt run/test/source freshness
  -> validation queries
  -> cost check
```

The project intentionally avoids Cloud Composer in this phase to prevent unnecessary managed-service cost while still demonstrating production-style Airflow patterns.

### Definition of Done

Phase 4 is considered complete when all of the following are true:

[x] Airflow runs locally
[x] Airflow runs in Docker Compose
[x] Postgres metadata DB is used in Docker Compose
[x] Webserver starts successfully
[x] Scheduler starts successfully
[x] DAG is detected by Airflow
[x] DAG has daily schedule
[x] catchup is disabled to avoid accidental historical runs
[x] Manual backfill is supported through dag_run.conf
[x] Historical backfill supports full_refresh=true
[x] dbt run, dbt test and dbt source freshness are separate Airflow tasks
[x] retries are configured
[x] execution timeouts are configured
[x] dagrun timeout is configured
[x] optional Slack failure callback exists
[x] no Slack secret is committed
[x] cost-check is part of the DAG
[x] raw validation is part of the DAG
[x] marts validation is part of the DAG
[x] full Docker backfill Jan 8-10 succeeded
[x] raw and marts reached 240 hourly rows
[x] BigQuery usage remains far below free-tier limits

### Final validated state

The final controlled historical backfill used:

```json
{
  "start_date": "2024-01-08",
  "end_date": "2024-01-10",
  "full_refresh": true
}
```

Validated warehouse state:

```
raw.raw_klines:
  rows_count: 240
  min_open_time: 2024-01-01 00:00:00
  max_open_time: 2024-01-10 23:00:00

marts.fact_price_features:
  rows_count: 240
  non_null_return_1h: 239
  non_null_log_return_1h: 239
  full_24h_windows: 217
  min_open_time: 2024-01-01 00:00:00
  max_open_time: 2024-01-10 23:00:00
```

### Cost state

The final cost check showed BigQuery usage still safely below the monthly free tier:

```
2026-05-20:
  query_jobs: 1168
  processed_mib: 6.1
  billed_mib: 6250.0
  billed_tib: 0.00596
```

This remains far below 1 TiB/month of BigQuery query processing.

### Important production lesson

During Phase 4.9, an intentional out-of-order historical run exposed a real incremental modeling issue:

```
2024-01-07 was loaded before 2024-01-06.
```

The dbt test assert_fact_prices_no_hourly_gaps correctly failed.

This validated that:

```
data-quality tests catch continuity gaps
scheduled runs can use normal incremental dbt
historical backfills may require full-refresh recovery
```

The DAG now supports:

```json
{
  "full_refresh": true
}
```

for controlled historical backfills.

### Final operational commands

Start Airflow Docker stack:

```bash
docker compose -f docker-compose.airflow.yml up -d airflow-webserver airflow-scheduler
```

List DAGs:

```bash
docker compose -f docker-compose.airflow.yml exec airflow-webserver \
  airflow dags list | grep market
```

Trigger controlled historical backfill:

```bash
docker compose -f docker-compose.airflow.yml exec airflow-webserver \
  airflow dags trigger market_data_platform_dev \
  --run-id manual_backfill_YYYY_MM_DD_to_YYYY_MM_DD_full_refresh \
  --conf '{"start_date":"YYYY-MM-DD","end_date":"YYYY-MM-DD","full_refresh":true}'
```

List runs:

```bash
docker compose -f docker-compose.airflow.yml exec airflow-webserver \
  airflow dags list-runs -d market_data_platform_dev
```

Validate warehouse:

```bash
make validate-raw
make validate-marts
make cost-check
```

Stop Airflow Docker stack:

```bash
docker compose -f docker-compose.airflow.yml down
```

Stop Airflow Docker stack and delete metadata DB volume:

```bash
docker compose -f docker-compose.airflow.yml down -v
```

Use down -v only when you intentionally want to reset local Airflow metadata.

## Dev scheduler safety note

During Phase 4 closeout, unpausing the daily scheduled DAG created a real scheduled
run for the latest Airflow interval. Because the development dataset is a small
historical demo range from 2024-01-01 to 2024-01-10, that scheduled run ingested
a live-date partition for 2026-05-19.

This correctly caused the dbt data-quality test `assert_fact_prices_no_hourly_gaps`
to fail, because the mart contained a large gap between the historical demo range
and the live scheduled date.

Resolution:

```text
1. Pause the DAG in dev.
2. Remove the accidental live-date GCS partition.
3. Reload raw from clean GCS partitions.
4. Rebuild marts with dbt full-refresh.
5. Re-run dbt tests and validation queries.
```

Final recovered state:

```
raw.raw_klines:
  rows_count: 240
  min_open_time: 2024-01-01 00:00:00
  max_open_time: 2024-01-10 23:00:00

marts.fact_price_features:
  rows_count: 240
  non_null_return_1h: 239
  non_null_log_return_1h: 239
  full_24h_windows: 217
  min_open_time: 2024-01-01 00:00:00
  max_open_time: 2024-01-10 23:00:00
```

In local development, the DAG should remain paused by default unless intentionally testing scheduler behavior. Manual backfills with explicit dag_run.conf are the preferred safe execution mode for the historical demo dataset.