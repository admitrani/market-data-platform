# Architecture

## Objective

The Market Data Platform provides a structured pipeline for ingesting, storing, transforming, validating, and serving financial market data.

The architecture separates data ingestion, storage, transformation, orchestration, infrastructure, and consumption so that each layer can evolve independently.

Architectural decisions and their tradeoffs are documented in [DECISIONS.md](DECISIONS.md).

## Current Deployment Scope

The current implementation is a development and portfolio environment.

- GCP provides object storage, the analytical warehouse, IAM, secrets, and Terraform remote state.
- Airflow runs locally through Docker Compose rather than Cloud Composer.
- The current dataset is a historical sample/backfill rather than a live production market feed.
- Cloud-touching CI workflows are deliberately controlled to limit GCP usage.
- No always-on production monitoring or managed orchestration service is deployed.

These constraints are intentional and keep the project inexpensive while preserving production-style architecture and development practices.

## High-Level Architecture

```text
                External APIs
                      │
                      ▼
              Python Ingestion
                      │
                      ▼
                 Raw Storage
            Google Cloud Storage
                      │
                      ▼
                 BigQuery Raw
                      │
                      ▼
               Transformation
                     dbt
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
     Staging     Intermediate      Marts
                                      │
                                      ▼
                                Serving Views
                                      │
                         ┌────────────┼────────────┐
                         ▼            ▼            ▼
                    Dashboards        ML        Research
```

Three supporting layers operate around the data flow:

```text
Airflow
  → orchestration, scheduling, retries, validation and recovery

Terraform
  → GCP infrastructure and remote state

GitHub Actions
  → code quality, CI, cloud validation and Terraform planning
```

## Data Flow

### 1. Ingestion

Python ingestion services retrieve external market data and write raw files to Google Cloud Storage.

The ingestion layer supports both:

- historical backfills
- incremental loads

Raw files are kept as immutable as practical so historical data can be reproduced or reprocessed.

### 2. Raw Warehouse

Raw market data is loaded from Google Cloud Storage into BigQuery.

The `raw` dataset acts as the warehouse entry point before transformation.

### 3. Transformation

dbt transforms raw data through separate logical layers:

- `staging`: cleaning and standardization
- `intermediate`: reusable transformation logic
- `marts`: analytics-ready and feature-ready datasets

dbt also provides schema tests, custom data-quality tests, source freshness checks, documentation, and lineage.

### 4. Serving

The mart layer exposes curated datasets for downstream use.

Current consumers include:

- dashboard serving views
- ML workflows
- quantitative research

Lower-level staging and intermediate models are not intended to be consumed directly by reporting or research applications.

## Orchestration

Airflow coordinates the development pipeline.

The current DAG runs:

```text
check_env
   │
   ▼
unit_tests
   │
   ▼
extract_load_gcs
   │
   ▼
load_bq_raw
   │
   ▼
dbt_run
   │
   ▼
dbt_test
   │
   ▼
dbt_source_freshness
   │
   ├── validate_raw
   ├── validate_marts
   └── cost_check
```

Airflow runs locally through Docker Compose with PostgreSQL as its metadata database.

The DAG includes:

- retries
- retry delays
- execution timeouts
- DAG run timeouts
- controlled historical backfills
- optional failure notification
- validation and cost checks as first-class tasks

Historical backfills can set `full_refresh=true` when older source data needs to rebuild incremental mart models.

The Makefile remains the stable command interface underneath Airflow, so orchestration does not duplicate pipeline business logic.

Full orchestration documentation is available in [docs/phase_4_orchestration.md](docs/phase_4_orchestration.md).

## Cloud Foundation

The cloud foundation is provisioned on Google Cloud Platform using Terraform.

### Provisioned Resources

- Google Cloud Storage bucket for raw market data.
- Google Cloud Storage bucket for Terraform remote state.
- BigQuery datasets:
  - `raw`
  - `staging`
  - `intermediate`
  - `marts`
  - `ci`
- Service account for pipeline workloads.
- Service account for GitHub Actions CI.
- IAM permissions for storage, BigQuery, Secret Manager, and Workload Identity Federation.
- Secret Manager for sensitive configuration.

## Resource Responsibilities

### Google Cloud Storage

Google Cloud Storage acts as the raw landing zone for externally ingested market data.

Raw files are treated as immutable whenever practical, supporting:

- reproducibility
- debugging
- historical reprocessing

A separate versioned GCS bucket stores Terraform remote state.

### BigQuery

BigQuery is the analytical warehouse.

Datasets are separated by responsibility:

- `raw`: externally ingested warehouse data
- `staging`: cleaned and standardized source models
- `intermediate`: reusable transformation models
- `marts`: analytics-ready and feature-ready datasets
- `ci`: isolated dbt CI builds

### Service Accounts

A dedicated pipeline service account is used for ingestion, transformation, and orchestration workloads.

A separate GitHub Actions CI service account is used for cloud validation.

This keeps CI permissions separate from pipeline execution permissions.

### Secret Manager

Secret Manager stores sensitive configuration and external API credentials.

Secrets are not committed to the repository or stored in plaintext project configuration.

## Infrastructure Management

Infrastructure is managed through Terraform under:

```text
infra/terraform/
```

Terraform is responsible for provisioning and versioning cloud resources.

State is stored remotely in Google Cloud Storage with versioning enabled.

GitHub Actions can run Terraform:

```text
fmt
init
validate
plan
```

but does not run:

```text
apply
```

Infrastructure changes therefore remain deliberate and require manual execution.

Direct changes through the Google Cloud Console should be avoided unless explicitly documented.

## Authentication

GitHub Actions authenticates to GCP through Workload Identity Federation.

This provides short-lived OIDC-based authentication and avoids long-lived service-account JSON keys in GitHub secrets.

Access is scoped through dedicated IAM bindings and a separate CI service account.

## CI/CD Architecture

```text
Developer
   │
   ▼
Pull Request
   │
   ▼
GitHub Actions
   │
   ├── Python lint and format checks
   ├── Unit tests
   ├── dbt parse
   ├── SQLFluff dbt SQL lint
   ├── Terraform fmt / validate
   └── Docker Compose config validation
```

Cloud-connected validation is separated from the required local quality gate:

```text
dbt CI
  → isolated BigQuery ci dataset

Terraform Plan
  → GCS remote state

GCP Auth Smoke Test
  → Workload Identity Federation
```

The `main` branch is protected.

Changes must go through pull requests and pass the required cloud-safe quality checks before merge.

Cloud-touching workflows are manual or path-scoped to keep CI predictable and control cost.

## Serving Layer

The mart layer includes dashboard-specific serving views so reporting does not depend directly on lower-level transformation models.

Current serving models include:

```text
marts.dashboard_price_timeseries
marts.dashboard_daily_summary
marts.dashboard_data_status
```

The serving layer is designed for lightweight dashboard consumption and can also expose curated datasets to other downstream applications.

See [docs/serving_dashboard.md](docs/serving_dashboard.md).

## Observability

The project uses lightweight observability rather than dedicated always-on monitoring infrastructure.

Checks cover:

- source freshness
- data coverage
- latest market timestamp
- latest load timestamp
- rolling-window completeness
- BigQuery usage and cost
- dbt tests and documentation

The platform distinguishes between:

```text
latest_market_bar_utc
```

and:

```text
latest_loaded_at
```

because recently loaded historical data is not necessarily recent market data.

See:

- [docs/data_sla.md](docs/data_sla.md)
- [docs/observability.md](docs/observability.md)

## Cost Control

The project is designed for a constrained GCP development budget.

Cost controls include:

- no always-on managed compute services
- no Cloud Composer
- no automatic Terraform apply in CI
- BigQuery byte limits through `maximum_bytes_billed`
- isolated `ci` dataset for dbt CI
- manual or path-scoped cloud workflows
- cloud-safe required pull-request checks
- lightweight observability instead of additional managed monitoring infrastructure

## Production Evolution

The current architecture deliberately keeps orchestration and monitoring local to control cost.

At larger scale, the same logical architecture could evolve toward:

- managed or containerized scheduled orchestration
- production alerting
- persisted observability metrics
- centralized monitoring dashboards
- larger or multi-asset datasets
- additional downstream consumers

These are future deployment options rather than features of the current implementation.

See [docs/scale_up_plan.md](docs/scale_up_plan.md) for the existing production scale-up plan.
