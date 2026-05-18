# Market Data Platform

Cloud-native market data platform for ingestion, transformation, orchestration, and analytics of financial market datasets.

## Goals

- Build production-style data engineering infrastructure
- Implement scalable ingestion pipelines
- Apply medallion architecture (Bronze / Silver / Gold)
- Use modern DE tooling:
  - Python
  - BigQuery
  - dbt
  - Airflow
  - Docker
  - Terraform
  - CI/CD

## Architecture

Documentation:
- `ARCHITECTURE.md`
- `DECISIONS.md`

## Project Structure

```text
ingestion/      # Python ingestion services
dbt/            # dbt models, tests, documentation and lineage
airflow/        # Airflow DAGs
infra/          # Terraform and Docker infrastructure
tests/          # Python tests
docs/           # diagrams, SLA docs and demo assets
```

## Cloud Foundation

The project uses Google Cloud Platform as the cloud foundation.

Provisioned resources:

- Google Cloud Storage raw bucket
- BigQuery datasets: `raw`, `staging`, `marts`, `ci`
- Pipeline service account
- Secret Manager secret
- IAM bindings managed through Terraform

Infrastructure code is located in:

```text
infra/terraform/
```

Terraform commands:

- cd infra/terraform
- terraform init
- terraform fmt
- terraform validate
- terraform plan