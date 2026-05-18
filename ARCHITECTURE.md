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