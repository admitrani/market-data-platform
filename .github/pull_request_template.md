## Summary

Briefly describe the change.

## Scope

- [ ] Ingestion
- [ ] Warehouse / BigQuery
- [ ] dbt
- [ ] Airflow / orchestration
- [ ] Terraform / infrastructure
- [ ] CI/CD
- [ ] Documentation

## Validation

- [ ] `make quality-cloud-safe` passes locally
- [ ] Python tests pass
- [ ] dbt parse passes
- [ ] SQLFluff passes
- [ ] Terraform validate/plan checked if infrastructure changed
- [ ] dbt CI checked if dbt models/tests/macros changed

## Cloud / Cost Impact

- [ ] No GCP resources created
- [ ] No always-on services added
- [ ] BigQuery byte limits respected
- [ ] Terraform apply not run from CI
- [ ] Cost impact reviewed

## Notes

Add any extra implementation notes, risks, or follow-up tasks.
