# Scale-Up Plan

## Objective

This document describes how the Market Data Platform could evolve from a cost-controlled portfolio project into a production-grade data platform.

## Current Design Constraints

The current project is intentionally designed for:

- GCP free-plan / free-trial cost control
- no always-on compute
- no Cloud Composer
- manual or path-scoped cloud workflows
- BTCUSDT 1h sample/backfill scope
- local Airflow orchestration

These constraints are deliberate and documented.

## Production Evolution

### 1. Data Scope

Current:

```text
BTCUSDT, 1h bars
```

Next:

```
Multiple symbols, multiple intervals, larger historical coverage
```

Potential additions:

- ETHUSDT
- SOLUSDT
- BTC spot and derivatives
- multiple exchanges
- trade-level or aggTrade data
- dollar bars / volume bars for quant research

### 2. Orchestration

Current:

```
Local/Docker Airflow
```

Production options:

- Cloud Composer
- Cloud Run Jobs + Cloud Scheduler
- GKE for larger workflows
- Prefect or Dagster

Recommended next step for cost control:

```
Cloud Run Jobs + Cloud Scheduler
```

This avoids the cost of always-on Composer while still providing cloud-native scheduling.

### 3. Data Quality and Contracts

Current:

- dbt tests
- SQLFluff
- source freshness
- observability SQL queries
- data SLA docs

Production additions:

- dbt exposures
- schema versioning
- consumer-facing data contracts
- Great Expectations or Soda checks if needed
- alerting on test failures
- persisted audit tables

### 4. Monitoring

Current:

- manual observability queries
- dbt freshness
- BigQuery usage query

Production additions:

- scheduled observability jobs
- Looker Studio operational dashboard
- alerting via Slack/email
- freshness failure notifications
- BigQuery cost anomaly checks

### 5. Infrastructure

Current:

- Terraform-managed GCP resources
- GCS remote state
- manual Terraform apply
- Terraform plan in CI

Production additions:

- separate dev/staging/prod environments
- remote state per environment
- stricter IAM boundaries
- Terraform module structure
- policy checks
- automated plan comments on PRs

### 6. CI/CD

Current:

- protected main branch
- required local quality gates
- dbt CI for relevant PRs
- WIF authentication
- no service account JSON keys

Production additions:

- environment-specific deployment workflows
- automatic dbt docs publishing
- PR comments with Terraform plan summaries
- artifact retention
- release tags
- stricter dependency pinning

### 7. Cost Optimization

Current:

- maximum bytes billed
- no always-on services
- manual cloud workflows

Production additions:

- table partition expiration policies
- clustering optimization
- incremental dbt models
- materialized views where useful
- reservation/slot analysis if scale justifies it
- lifecycle policies for raw GCS objects

### 8. Security

Current:

- WIF for GitHub Actions
- service accounts
- Secret Manager
- no committed secrets

Production additions:

- least-privilege consumer accounts
- authorized views
- dataset-level IAM separation
- audit logging review
- secret rotation
- VPC Service Controls if justified

## Recommended Next Production Step

The most practical next step would be:

```
Cloud Run Job + Cloud Scheduler for ingestion
```

Why:

- lower cost than Cloud Composer
- cloud-native
- no always-on worker
- simple for one or a few scheduled jobs
- good fit for the current project scale

## What Not To Do Yet

Avoid:

- Cloud Composer before clear need
- Kubernetes before workload complexity justifies it
- real-time streaming before batch SLAs are mature
- multi-asset expansion before current observability and contracts are stable
- over-engineered abstractions too early
