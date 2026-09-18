# Market Data Platform

Cloud-based market data platform for ingesting, transforming, validating, and serving financial market data on GCP.

## Overview

The platform ingests hourly market data with Python, stores raw data in Google Cloud Storage and BigQuery, and transforms it with dbt into analytics-ready datasets.

Airflow orchestrates ingestion, warehouse loading, transformations, data-quality checks, and cost validation. Terraform manages the GCP infrastructure, while GitHub Actions provides automated quality gates and controlled cloud validation.

The current implementation is a cost-controlled development and portfolio environment built around a historical market-data backfill, not a live production trading feed.

## Architecture

```text
External APIs
      │
      ▼
Python Ingestion
      │
      ▼
Google Cloud Storage
      │
      ▼
BigQuery Raw
      │
      ▼
dbt
      │
      ├── Staging
      ├── Intermediate
      └── Marts
            │
            ▼
     Serving Views
            │
            ▼
 Dashboards / ML / Research
```

Supporting layers:

```text
Airflow         → pipeline orchestration, retries and validation
Docker          → reproducible local orchestration environment
Terraform       → GCP infrastructure
GitHub Actions  → CI/CD and cloud validation
```

For the full architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).

Key architectural decisions are documented in [DECISIONS.md](DECISIONS.md).

## Key Capabilities

- Python ingestion for historical backfills and incremental market-data loads.
- Raw storage in Google Cloud Storage with analytical datasets in BigQuery.
- dbt models across staging, intermediate, and mart layers with automated data-quality testing.
- Airflow orchestration for ingestion, loading, transformation, freshness checks, validation, and cost monitoring.
- Docker-based local Airflow environment with PostgreSQL metadata storage.
- Terraform-managed GCP infrastructure and remote state.
- GitHub Actions for code quality, dbt CI, Terraform planning, and GCP authentication checks.
- Keyless GitHub-to-GCP authentication using Workload Identity Federation.
- BigQuery usage limits and cloud-safe CI workflows to keep infrastructure costs controlled.
- Curated serving views for dashboards and downstream ML or research workflows.
- Lightweight observability for freshness, data coverage, and BigQuery usage.

## Tech Stack

Python · SQL · GCP · Google Cloud Storage · BigQuery · dbt · Airflow · Docker · Terraform · GitHub Actions

## Local Development

The Makefile is the main development interface.

Common cloud-safe commands:

```bash
make lint
make test
make dbt-parse
make sql-lint
make terraform-check
make docker-check
make quality-cloud-safe
```

Cloud-touching commands are intentionally separate:

```bash
make dbt-ci-build
make ingest-backfill
make ingest-incremental
make load-bq-raw
make dbt-build
```

The full local development pipeline can be executed with:

```bash
make phase4-dev
```

## CI/CD

GitHub Actions is used for automated quality gates, controlled cloud validation, and infrastructure planning.

| Workflow | Trigger | Cloud access | Purpose |
|---|---|---:|---|
| CI | push / pull request | No | Python lint, unit tests, dbt parse, SQLFluff, Terraform validation, Docker Compose validation |
| dbt CI | manual | BigQuery `ci` dataset | Build and test dbt models in an isolated CI dataset |
| Terraform Plan | manual / Terraform PR changes | GCS remote state | Validate infrastructure changes without applying them |
| GCP Auth Smoke Test | manual | IAM / OIDC only | Validate GitHub Actions authentication to GCP |

The `main` branch is protected. Changes go through pull requests and must pass the required cloud-safe quality checks before merge.

Cloud-touching workflows are kept manual or path-scoped to avoid unnecessary GCP usage.

## Infrastructure & Security

Cloud infrastructure is managed with Terraform.

Provisioned resources include:

- Google Cloud Storage for raw market data.
- Google Cloud Storage for Terraform remote state.
- BigQuery datasets for raw, staging, intermediate, mart, and CI workloads.
- Dedicated service accounts for pipeline and CI workloads.
- IAM bindings managed through Terraform.
- Secret Manager for sensitive configuration.

GitHub Actions authenticates to GCP through Workload Identity Federation rather than committed service-account JSON keys.

Terraform CI runs `plan`, but never automatically runs `apply`.

## Cost Guardrails

The project is designed to operate within a constrained GCP development budget.

Controls include:

- No always-on managed compute services.
- No Cloud Composer.
- No automatic Terraform apply in CI.
- BigQuery queries use `maximum_bytes_billed`.
- dbt CI writes to an isolated `ci` dataset.
- Cloud-touching workflows are manual or path-scoped.
- Required pull-request checks remain cloud-safe.

## Orchestration

Airflow runs locally through Docker Compose rather than Cloud Composer.

The DAG separates the main pipeline stages:

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

The orchestration layer includes retries, execution timeouts, DAG timeouts, controlled historical backfills, and optional failure notifications.

Historical backfills can request a full dbt refresh when older data is loaded after newer incremental data.

See [docs/phase_4_orchestration.md](docs/phase_4_orchestration.md) for the full orchestration design and runbook.

## Serving & Observability

The mart layer exposes curated views for downstream consumption, including dashboard-ready datasets.

The repository also includes lightweight operational checks for:

- source freshness
- market-data coverage
- latest load status
- rolling-window completeness
- BigQuery usage and cost

See:

- [Serving dashboard](docs/serving_dashboard.md)
- [Data SLA](docs/data_sla.md)
- [Observability](docs/observability.md)

## Project Structure

```text
ingestion/        # Python ingestion services
warehouse/        # BigQuery loading and validation utilities
dbt/              # dbt models, tests, documentation and lineage
orchestration/    # Airflow DAGs
infra/terraform/  # Terraform infrastructure-as-code
docker/           # Docker images and runtime configuration
tests/            # Python unit tests
docs/             # Architecture, operations and portfolio documentation
```

## Documentation

Additional documentation includes:

- [ARCHITECTURE.md](ARCHITECTURE.md) - system architecture and infrastructure design
- [DECISIONS.md](DECISIONS.md) - architectural decision records
- [docs/phase_4_orchestration.md](docs/phase_4_orchestration.md) - Airflow orchestration and runbook
- [docs/data_sla.md](docs/data_sla.md) - freshness, quality, and cost-control expectations
- [docs/observability.md](docs/observability.md) - operational visibility and monitoring
- [docs/scale_up_plan.md](docs/scale_up_plan.md) - how the platform could evolve at production scale
- [docs/serving_dashboard.md](docs/serving_dashboard.md) - dashboard serving layer
- [docs/trading_v2_integration.md](docs/trading_v2_integration.md) - downstream ML and research integration

## Current Scope

The current dataset is a historical development sample rather than a continuously running market feed.

Airflow is deployed locally through Docker Compose, and the project intentionally avoids always-on managed orchestration and monitoring services to keep cloud costs low.

The architecture is designed so those components can be replaced with managed production infrastructure without changing the core data model or pipeline structure.
