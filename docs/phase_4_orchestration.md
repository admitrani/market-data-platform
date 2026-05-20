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
````

instead of:

```
dbt-run
````

This rebuilds the marts from raw data and removes gaps created by out-of-order historical loads.

This behavior was validated after an intentional out-of-order run caused assert_fact_prices_no_hourly_gaps to fail. Running dbt-run-full-refresh rebuilt the mart to 168 continuous hourly rows from 2024-01-01 00:00:00 to 2024-01-07 23:00:00, and all 72 dbt tests passed.