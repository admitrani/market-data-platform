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