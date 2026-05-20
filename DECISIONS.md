# Architecture Decisions

This document tracks the main architectural and infrastructure decisions made throughout the project.

Each decision includes:
- context
- rationale
- tradeoffs
- future implications

---

## ADR-001 — Medallion Architecture

### Context

The platform requires a scalable and maintainable structure for handling raw, cleaned, and analytics-ready datasets.

### Decision

Adopt a medallion architecture composed of:

- Bronze layer
  - raw immutable ingestion data
- Silver layer
  - cleaned and validated datasets
- Gold layer
  - analytics and ML-ready datasets

### Rationale

Benefits:
- clear separation of concerns
- reproducibility
- easier debugging
- incremental transformations
- scalable pipeline organization

### Tradeoffs

- additional storage duplication
- more pipeline complexity

### Consequences

Future pipelines and dbt models must respect layer boundaries.

---

## ADR-002 — BigQuery as Analytical Warehouse

### Context

The platform requires a scalable analytical warehouse capable of handling large market datasets efficiently.

### Decision

Use Google BigQuery as the primary analytical warehouse.

### Rationale

Benefits:
- serverless architecture
- scalable query execution
- strong integration with GCP ecosystem
- native compatibility with dbt
- industry relevance for data engineering roles

### Tradeoffs

- query cost management required
- vendor lock-in to GCP ecosystem

### Consequences

Warehouse modeling and transformations will be optimized for BigQuery SQL patterns.

---

## ADR-003 — dbt for Transformations

### Context

The project requires maintainable SQL-based transformations with lineage, testing, and modularity.

### Decision

Use dbt-core as the transformation framework.

### Rationale

Benefits:
- modular SQL transformations
- lineage tracking
- testing support
- documentation generation
- industry-standard modern data stack tool

### Tradeoffs

- additional project complexity
- dependency on SQL-centric workflows

### Consequences

Transformations should be implemented primarily through dbt models instead of standalone Python scripts.

---

## ADR-004 — Terraform for Infrastructure-as-Code

### Context

Cloud resources must be reproducible, versioned, and deployable consistently across environments.

### Decision

Use Terraform to provision infrastructure resources.

### Rationale

Benefits:
- reproducible infrastructure
- version-controlled deployments
- environment consistency
- industry-standard IaC tooling

### Tradeoffs

- steeper learning curve
- additional operational complexity

### Consequences

All cloud infrastructure should be provisioned through Terraform rather than manual console configuration.

---

## ADR-005 — Google Cloud Storage as Raw Landing Zone

### Context

The platform requires a durable and scalable location for externally ingested market data before transformation.

### Decision

Use Google Cloud Storage as the raw landing zone.

### Rationale

Benefits:
- scalable object storage
- strong integration with BigQuery and GCP
- suitable for immutable raw data
- supports historical reprocessing
- widely used in production data platforms

### Tradeoffs

- requires cloud billing setup
- requires lifecycle and access management
- raw files must be carefully organized to avoid data lake disorder

### Consequences

Raw ingested data should first land in GCS before being loaded or transformed downstream.

---

## ADR-006 — Dedicated Pipeline Service Account

### Context

The platform requires secure execution of ingestion, transformation, and orchestration workloads.

### Decision

Create a dedicated service account for pipeline workloads.

### Rationale

Benefits:
- avoids using personal user credentials
- supports least-privilege IAM design
- prepares the project for Airflow and CI/CD execution
- improves auditability

### Tradeoffs

- requires IAM configuration
- permissions must be maintained as the platform grows

### Consequences

Pipeline code should eventually authenticate through this service account rather than through a personal Google account.

---

## ADR-007 — Secret Manager for Sensitive Configuration

### Context

The platform may require API keys or credentials for external market data providers.

### Decision

Use Google Secret Manager for sensitive values.

### Rationale

Benefits:
- avoids committing secrets to Git
- centralizes sensitive configuration
- integrates with IAM
- supports future production-style deployment

### Tradeoffs

- adds dependency on GCP
- requires secret access permissions
- local development requires a clear authentication strategy

### Consequences

API keys and sensitive values must not be stored in plaintext files such as `.env`, YAML configs, or source code.

---

## ADR-008 — Docker Compose for Local Development

### Context

The project requires a reproducible local development environment for services such as ingestion, dbt, and Airflow.

### Decision

Use Docker Compose as the local orchestration layer for development services.

### Rationale

Benefits:
- reproducible local environment
- simplified service startup
- avoids machine-specific setup issues
- prepares the project for Airflow and dbt containers
- aligns with production-style engineering practices

### Tradeoffs

- adds containerization complexity
- requires Docker installed locally
- local Compose does not fully replicate production cloud infrastructure

### Consequences

Local development services should be added to `docker-compose.yml` incrementally as the platform evolves.

---

## ADR-009 — GitHub Actions for CI/CD

### Context

The platform requires automated quality checks to make the repository behave like a production-style data engineering project.

### Decision

Use GitHub Actions as the CI/CD layer.

### Rationale

Benefits:
- validates changes automatically on pull requests
- improves engineering discipline
- creates a professional portfolio signal
- separates cloud-safe checks from cloud-touching workflows

### Tradeoffs

- requires workflow maintenance
- CI dependency versions must be managed

### Consequences

Pull requests must pass the local quality workflow before merging to `main`.

---

## ADR-010 — Workload Identity Federation for GitHub to GCP Authentication

### Context

GitHub Actions needs controlled access to Google Cloud for dbt CI, Terraform plan, and authentication smoke tests.

### Decision

Use Google Cloud Workload Identity Federation instead of service account JSON keys.

### Rationale

Benefits:
- avoids long-lived credentials in GitHub secrets
- improves security posture
- aligns with modern cloud IAM practices
- restricts access to the specific GitHub repository

### Tradeoffs

- initial setup is more complex
- IAM bindings and provider configuration must be documented

### Consequences

GitHub Actions authenticates using OIDC and a dedicated `github-actions-ci` service account.

---

## ADR-011 — Isolated BigQuery `ci` Dataset for dbt CI

### Context

dbt CI needs to build and test models without modifying development marts or production-like datasets.

### Decision

Use a dedicated BigQuery dataset named `ci` for dbt CI builds.

### Rationale

Benefits:
- isolates CI writes from development datasets
- makes test artifacts easy to inspect and clean
- prevents accidental modification of `staging`, `intermediate`, or `marts`
- supports low-cost controlled CI validation

### Tradeoffs

- duplicates some dbt objects during CI runs
- requires schema-generation logic to route all CI models into `ci`

### Consequences

The dbt `generate_schema_name` macro routes all models to `target.schema` when `target.name == "ci"`.

---

## ADR-012 — BigQuery Cost Guardrails in CI

### Context

The project runs on a constrained GCP free plan / free trial budget.

### Decision

Use `maximum_bytes_billed` and separate manual workflows for cloud-touching jobs.

### Rationale

Benefits:
- prevents unexpectedly large BigQuery scans
- keeps CI predictable
- reduces risk of accidental cloud spending
- makes cost control explicit in the repository

### Tradeoffs

- some legitimate dbt builds can fail if the byte limit is too low
- thresholds may need adjustment as data volume grows

### Consequences

dbt CI uses `BQ_MAX_BYTES` and cloud-touching workflows are not part of the always-required pull request gate.

---

## ADR-013 — Terraform Remote State in Google Cloud Storage

### Context

Terraform initially used local state, which is not suitable for CI-based planning.

### Decision

Store Terraform state remotely in a dedicated Google Cloud Storage bucket.

### Rationale

Benefits:
- enables Terraform plan in GitHub Actions
- avoids state drift between machines
- supports state versioning
- improves reproducibility and collaboration readiness

### Tradeoffs

- adds one additional GCP resource
- requires bucket IAM permissions for the CI service account

### Consequences

Terraform CI runs `plan` against remote state but does not run `apply`.

---

## ADR-014 — No Terraform Apply in CI

### Context

Infrastructure changes should be reviewed carefully, especially in a cost-constrained cloud project.

### Decision

GitHub Actions can run Terraform format, init, validate, and plan, but not apply.

### Rationale

Benefits:
- avoids accidental infrastructure changes
- keeps human approval in the loop
- reduces billing risk
- still validates infrastructure changes before merge

### Tradeoffs

- infrastructure deployment remains manual
- requires the developer to run apply intentionally when needed

### Consequences

Any Terraform apply must be executed manually and deliberately.

---

## ADR-015 — SQLFluff for dbt SQL Quality

### Context

The repository contains dbt SQL models and custom data tests that should follow consistent style rules.

### Decision

Use SQLFluff with the BigQuery dialect and dbt templater.

### Rationale

Benefits:
- validates SQL style automatically
- supports dbt-aware linting
- improves maintainability of SQL models
- catches formatting drift before merge

### Tradeoffs

- adds one more CI dependency
- SQL lint rules may need tuning to avoid excessive noise

### Consequences

`sql-lint` is part of the cloud-safe local quality gate.

---

## ADR-016 — Protected Main Branch

### Context

The repository should prevent direct changes to `main` and require automated checks before merge.

### Decision

Protect the `main` branch and require pull requests with the `Local quality gates` check passing.

### Rationale

Benefits:
- prevents unreviewed direct pushes
- enforces CI discipline
- simulates a professional team workflow
- improves portfolio credibility

### Tradeoffs

- small changes require a branch and pull request
- some workflows remain manual to avoid unnecessary cloud usage

### Consequences

All changes must go through branches and pull requests.
