# Architecture

## Objective

Build a cloud-native market data platform capable of:

- ingesting market datasets
- storing raw and processed data
- orchestrating scalable pipelines
- transforming datasets for analytics and ML workflows

---

## High-Level Architecture

```text
                External APIs
                      │
                      ▼
              Ingestion Services
                      │
                      ▼
                 Raw Storage
               (Google Cloud Storage)
                      │
                      ▼
                 BigQuery Raw
                      │
                      ▼
               Transformation Layer
                    (dbt)
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
      Silver Layer            Gold Layer
   cleaned datasets      analytics/features
                      │
                      ▼
                 Consumption
          dashboards / ML / research

---

## Cloud Foundation

The initial cloud foundation is provisioned on Google Cloud Platform using Terraform.

### Provisioned Resources

- Google Cloud Storage bucket for raw market data
- BigQuery datasets:
  - `raw`
  - `staging`
  - `marts`
  - `ci`
- Service account for pipeline workloads
- IAM permissions for storage, BigQuery, and secrets access
- Secret Manager secret for external API credentials

### Resource Responsibilities

#### Google Cloud Storage

Google Cloud Storage is used as the raw landing zone for externally ingested market data.

Raw files should be treated as immutable whenever possible. This enables reproducibility, debugging, and historical reprocessing.

#### BigQuery

BigQuery is used as the analytical warehouse.

Datasets are separated by responsibility:

- `raw`: externally ingested data loaded into warehouse tables
- `staging`: cleaned and standardized source models
- `marts`: analytics-ready models for downstream consumption
- `ci`: isolated dataset for automated tests and CI/CD workflows

#### Service Account

A dedicated service account is used for pipeline execution.

This avoids relying on personal user credentials and prepares the platform for future orchestration through Airflow and CI/CD.

#### Secret Manager

Secret Manager is used to store external API credentials and sensitive configuration.

Secrets should not be committed to the repository or stored in plaintext configuration files.

---

## Infrastructure Management

Infrastructure is managed with Terraform under:

```text
infra/terraform/

Terraform is responsible for provisioning and versioning cloud resources.

Manual changes through the Google Cloud Console should be avoided unless explicitly documented.