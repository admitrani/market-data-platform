.PHONY: help check-env test ingest-backfill ingest-incremental load-bq-raw dbt-build dbt-run dbt-run-full-refresh dbt-test dbt-source-freshness dbt-docs validate-raw validate-marts cost-check phase4-dev airflow-check airflow-db-migrate airflow-dag-list airflow-dag-test

-include config/pipeline_dev.env

PROJECT_ID ?= $(shell gcloud config get-value project 2>/dev/null)
TF_DIR ?= infra/terraform
RAW_BUCKET ?= $(shell cd $(TF_DIR) && terraform output -raw raw_bucket_name 2>/dev/null)
BQ_LOCATION ?= europe-west1

SYMBOL ?= BTCUSDT
INTERVAL ?= 1h
START_DATE ?= 2024-01-01
END_DATE ?= 2024-01-05

BQ_MAX_BYTES ?= 52428800

export PROJECT_ID RAW_BUCKET BQ_LOCATION SYMBOL INTERVAL START_DATE END_DATE BQ_MAX_BYTES AIRFLOW_RETRIES AIRFLOW_RETRY_DELAY_MINUTES AIRFLOW_TASK_TIMEOUT_MINUTES AIRFLOW_DAG_TIMEOUT_MINUTES AIRFLOW_SLA_MINUTES

AIRFLOW_HOME ?= $(PWD)/.airflow_home
AIRFLOW_DAGS_FOLDER ?= $(PWD)/orchestration/airflow/dags
AIRFLOW_BIN ?= $(PWD)/.venv-airflow/bin/airflow
AIRFLOW_DAG_ID ?= market_data_platform_dev
AIRFLOW_TEST_DATE ?= 2024-01-03

help:
	@echo "Market Data Platform orchestration"
	@echo ""
	@echo "Core targets:"
	@echo "  make test"
	@echo "  make ingest-backfill START_DATE=2024-01-01 END_DATE=2024-01-05"
	@echo "  make ingest-incremental END_DATE=2024-01-05"
	@echo "  make load-bq-raw"
	@echo "  make dbt-build"
	@echo "  make validate-raw"
	@echo "  make validate-marts"
	@echo "  make cost-check"
	@echo "  make phase4-dev"
	@echo ""
	@echo "Current defaults:"
	@echo "  PROJECT_ID=$(PROJECT_ID)"
	@echo "  RAW_BUCKET=$(RAW_BUCKET)"
	@echo "  BQ_LOCATION=$(BQ_LOCATION)"
	@echo "  SYMBOL=$(SYMBOL)"
	@echo "  INTERVAL=$(INTERVAL)"
	@echo "  START_DATE=$(START_DATE)"
	@echo "  END_DATE=$(END_DATE)"
	@echo "  BQ_MAX_BYTES=$(BQ_MAX_BYTES)"

check-env:
	@test -n "$(PROJECT_ID)" || (echo "PROJECT_ID is empty. Run: gcloud config set project <project-id>" && exit 1)
	@test -n "$(RAW_BUCKET)" || (echo "RAW_BUCKET is empty. Check Terraform output: cd infra/terraform && terraform output" && exit 1)
	@echo "Environment OK"
	@echo "PROJECT_ID=$(PROJECT_ID)"
	@echo "RAW_BUCKET=$(RAW_BUCKET)"
	@echo "BQ_LOCATION=$(BQ_LOCATION)"

test:
	pytest tests/ingestion tests/warehouse -v

ingest-backfill: check-env
	python -m ingestion.cli backfill --bucket "$(RAW_BUCKET)" --symbol "$(SYMBOL)" --interval "$(INTERVAL)" --start-date "$(START_DATE)" --end-date "$(END_DATE)"

ingest-incremental: check-env
	python -m ingestion.cli incremental --bucket "$(RAW_BUCKET)" --symbol "$(SYMBOL)" --interval "$(INTERVAL)" --bootstrap-start-date "$(START_DATE)" --end-date "$(END_DATE)"

load-bq-raw: check-env
	python -m ingestion.cli load-bq-raw --project-id "$(PROJECT_ID)" --dataset-id raw --table-id raw_klines --gcs-uri "gs://$(RAW_BUCKET)/raw/source=binance_spot/dataset=klines/symbol=$(SYMBOL)/interval=$(INTERVAL)/date=*/data.parquet"

dbt-build: check-env
	dbt build --project-dir dbt --profiles-dir dbt --no-partial-parse

dbt-run: check-env
	dbt run --project-dir dbt --profiles-dir dbt --no-partial-parse

dbt-run-full-refresh: check-env
	dbt run --project-dir dbt --profiles-dir dbt --no-partial-parse --full-refresh

dbt-test: check-env
	dbt test --project-dir dbt --profiles-dir dbt --no-partial-parse

dbt-source-freshness: check-env
	dbt source freshness --project-dir dbt --profiles-dir dbt --no-partial-parse

dbt-docs: check-env
	dbt docs generate --project-dir dbt --profiles-dir dbt --no-partial-parse

validate-raw: check-env
	bq query --location="$(BQ_LOCATION)" --use_legacy_sql=false --maximum_bytes_billed="$(BQ_MAX_BYTES)" "SELECT symbol, \`interval\`, COUNT(*) AS rows_count, MIN(open_time_utc) AS min_open_time, MAX(open_time_utc) AS max_open_time FROM \`$(PROJECT_ID).raw.raw_klines\` GROUP BY symbol, \`interval\`"

validate-marts: check-env
	bq query --location="$(BQ_LOCATION)" --use_legacy_sql=false --maximum_bytes_billed="$(BQ_MAX_BYTES)" "SELECT symbol, bar_interval, COUNT(*) AS rows_count, COUNTIF(return_1h IS NOT NULL) AS non_null_return_1h, COUNTIF(log_return_1h IS NOT NULL) AS non_null_log_return_1h, COUNTIF(rolling_window_observations_24h = 24) AS full_24h_windows, MIN(open_time_utc) AS min_open_time, MAX(open_time_utc) AS max_open_time FROM \`$(PROJECT_ID).marts.fact_price_features\` GROUP BY symbol, bar_interval"

cost-check: check-env
	bq query --location="$(BQ_LOCATION)" --use_legacy_sql=false --maximum_bytes_billed="$(BQ_MAX_BYTES)" "SELECT DATE(creation_time) AS usage_date, COUNT(*) AS query_jobs, ROUND(SUM(total_bytes_processed) / POW(1024, 2), 2) AS processed_mib, ROUND(SUM(total_bytes_billed) / POW(1024, 2), 2) AS billed_mib, ROUND(SUM(total_bytes_billed) / POW(1024, 4), 6) AS billed_tib FROM \`$(PROJECT_ID).region-europe-west1.INFORMATION_SCHEMA.JOBS_BY_PROJECT\` WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY) AND job_type = 'QUERY' GROUP BY usage_date ORDER BY usage_date DESC"

phase4-dev: check-env test ingest-backfill load-bq-raw dbt-build validate-raw validate-marts cost-check
	@echo "Phase 4 dev orchestration completed successfully."

airflow-check:
	@test -x "$(AIRFLOW_BIN)" || (echo "Airflow binary not found at $(AIRFLOW_BIN). Create .venv-airflow first." && exit 1)
	@echo "Airflow OK"
	@echo "AIRFLOW_HOME=$(AIRFLOW_HOME)"
	@echo "AIRFLOW_DAGS_FOLDER=$(AIRFLOW_DAGS_FOLDER)"
	@echo "AIRFLOW_DAG_ID=$(AIRFLOW_DAG_ID)"

airflow-db-migrate: airflow-check
	AIRFLOW_HOME="$(AIRFLOW_HOME)" \
	AIRFLOW__CORE__DAGS_FOLDER="$(AIRFLOW_DAGS_FOLDER)" \
	AIRFLOW__CORE__LOAD_EXAMPLES=False \
	"$(AIRFLOW_BIN)" db migrate

airflow-dag-list: airflow-check
	AIRFLOW_HOME="$(AIRFLOW_HOME)" \
	AIRFLOW__CORE__DAGS_FOLDER="$(AIRFLOW_DAGS_FOLDER)" \
	AIRFLOW__CORE__LOAD_EXAMPLES=False \
	"$(AIRFLOW_BIN)" dags list | grep "$(AIRFLOW_DAG_ID)"

airflow-dag-test: airflow-check
	AIRFLOW_HOME="$(AIRFLOW_HOME)" \
	AIRFLOW__CORE__DAGS_FOLDER="$(AIRFLOW_DAGS_FOLDER)" \
	AIRFLOW__CORE__LOAD_EXAMPLES=False \
	"$(AIRFLOW_BIN)" dags test "$(AIRFLOW_DAG_ID)" "$(AIRFLOW_TEST_DATE)"

