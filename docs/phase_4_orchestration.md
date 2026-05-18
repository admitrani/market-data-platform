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