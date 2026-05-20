# Architecture

## Objective

Build a cloud-native market data platform capable of:

- ingesting market datasets
- storing raw and processed data
- orchestrating scalable pipelines
- transforming datasets for analytics and ML workflows
- validating changes through CI/CD and infrastructure-as-code workflows

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
        ┌─────────────┴─────────────┐
        ▼                           ▼
   Staging / Intermediate        Marts
 cleaned & normalized       analytics/features
                      │
                      ▼
                 Consumption
          dashboards / ML / research
```

---

## Cloud Foundation

The initial cloud foundation is provisioned on Google Cloud Platform using Terraform.

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
- IAM permissions for storage, BigQuery, secrets access, and Workload Identity Federation.
- Secret Manager secret for external API credentials.

### Resource Responsibilities

#### Google Cloud Storage

Google Cloud Storage is used as the raw landing zone for externally ingested market data.

Raw files should be treated as immutable whenever possible. This enables reproducibility, debugging, and historical reprocessing.

A separate GCS bucket stores Terraform remote state with versioning enabled.

#### BigQuery

BigQuery is used as the analytical warehouse.

Datasets are separated by responsibility:

- `raw`: externally ingested data loaded into warehouse tables.
- `staging`: cleaned and standardized source models.
- `intermediate`: reusable intermediate dbt models.
- `marts`: analytics-ready models for downstream consumption.
- `ci`: isolated dataset for automated dbt CI workflows.

#### Service Accounts

A dedicated pipeline service account is used for ingestion, transformation, and orchestration workloads.

A separate GitHub Actions CI service account is used by Workload Identity Federation. This avoids long-lived service account keys and limits CI permissions.

#### Secret Manager

Secret Manager is used to store external API credentials and sensitive configuration.

Secrets should not be committed to the repository or stored in plaintext configuration files.

---

## CI/CD Architecture

```text
Developer
   │
   ▼
Pull Request
   │
   ▼
GitHub Actions: CI
   │
   ├── Python lint and format checks
   ├── Unit tests
   ├── dbt parse
   ├── SQLFluff dbt SQL lint
   ├── Terraform fmt / validate
   └── Docker Compose config validation

Manual / path-scoped workflows:
   │
   ├── dbt CI → BigQuery ci dataset
   ├── Terraform Plan → GCS remote state
   └── GCP Auth Smoke Test → Workload Identity Federation
```

### Required Pull Request Gate

The required branch protection check is limited to cloud-safe local quality gates.

Cloud-touching workflows are manual or path-scoped to control GCP costs.

---

## Infrastructure Management

Infrastructure is managed with Terraform under:

```text
infra/terraform/
```

Terraform is responsible for provisioning and versioning cloud resources.

Terraform state is stored remotely in Google Cloud Storage.

GitHub Actions can run Terraform plan, but not Terraform apply.

Manual changes through the Google Cloud Console should be avoided unless explicitly documented.

---

## Cost Control

The project is designed for a GCP free plan / free trial budget.

Cost controls include:

- no always-on compute services
- no Cloud Composer
- no automatic Terraform apply in CI
- BigQuery byte limits through `maximum_bytes_billed`
- isolated `ci` dataset for dbt CI
- manual cloud-touching workflows where appropriate
- branch protection with cloud-safe required checks
