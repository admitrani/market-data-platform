# Market Data Platform

Cloud-native market data platform for ingestion, transformation, orchestration, CI/CD, and analytics of financial market datasets.

## Goals

- Build production-style data engineering infrastructure.
- Implement scalable ingestion pipelines.
- Apply medallion architecture across raw, staging/intermediate, and mart layers.
- Use modern data engineering tooling:
  - Python
  - Google Cloud Storage
  - BigQuery
  - dbt
  - Airflow
  - Docker
  - Terraform
  - GitHub Actions
  - SQLFluff
  - pre-commit

## Architecture Documentation

- `ARCHITECTURE.md`
- `DECISIONS.md`

## Project Structure

```text
ingestion/        # Python ingestion services
warehouse/        # BigQuery loading utilities
dbt/              # dbt models, tests, documentation and lineage
orchestration/    # Airflow DAGs
infra/terraform/  # Terraform infrastructure-as-code
docker/           # Docker images and runtime configuration
tests/            # Python unit tests
docs/             # diagrams, SLA docs and demo assets
```

## Cloud Foundation

The project uses Google Cloud Platform as the cloud foundation.

Provisioned resources:

- Google Cloud Storage raw bucket.
- BigQuery datasets:
  - `raw`
  - `staging`
  - `intermediate`
  - `marts`
  - `ci`
- Pipeline service account.
- Secret Manager secret.
- IAM bindings managed through Terraform.
- Terraform remote state bucket in Google Cloud Storage.

Infrastructure code is located in:

```text
infra/terraform/
```

Core Terraform commands:

```bash
terraform -chdir=infra/terraform fmt
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan -refresh=false
```

## Local Development

The project uses Makefile targets as the main local development entrypoint.

Common commands:

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

## CI/CD

The repository uses GitHub Actions for quality gates, controlled cloud validation, and infrastructure planning.

| Workflow | Trigger | Cloud access | Purpose |
|---|---|---:|---|
| CI | push / pull request | No | Python lint, unit tests, dbt parse, SQLFluff, Terraform validate, Docker Compose config |
| dbt CI | manual | BigQuery `ci` dataset | Controlled dbt build/test in isolated CI dataset |
| Terraform Plan | manual / pull request on Terraform changes | GCS remote state | Terraform plan without apply |
| GCP Auth Smoke Test | manual | IAM/OIDC only | Validate GitHub Actions authentication to GCP |

Required pull request checks are intentionally limited to cloud-safe checks to control cost on the GCP free plan.

## Authentication

GitHub Actions authenticates to Google Cloud using Workload Identity Federation.

The project does not use committed service account JSON keys.

## Cost Guardrails

The project is designed to stay within the GCP free plan / free trial constraints.

Guardrails include:

- No always-on compute services.
- No Cloud Composer.
- No automatic Terraform apply in CI.
- dbt CI writes only to the isolated `ci` dataset.
- BigQuery jobs use `maximum_bytes_billed`.
- Cloud-touching workflows are manual or path-scoped.
- Branch protection requires local quality gates before merging.

## Branch Protection

The `main` branch is protected.

Changes must be introduced through pull requests and pass the required `Local quality gates` status check before merge.
