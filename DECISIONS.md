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
