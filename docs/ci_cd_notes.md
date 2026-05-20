# CI/CD Notes

This repository uses GitHub Actions for local quality gates, dbt CI, Terraform plan validation, and GCP authentication through Workload Identity Federation.

Required PR checks are intentionally limited to cloud-safe checks. Cloud-touching workflows remain manual or path-scoped to control costs on the GCP free plan.
