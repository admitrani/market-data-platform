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
services/       # reusable services
pipelines/      # medallion pipelines
infra/          # infrastructure-as-code
orchestration/  # workflow orchestration
monitoring/     # observability & quality