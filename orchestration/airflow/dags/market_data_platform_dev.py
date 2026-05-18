"""Local Airflow DAG for the Market Data Platform dev pipeline.

This DAG intentionally orchestrates Makefile targets instead of duplicating
pipeline logic inside Airflow. The Makefile remains the reproducible command
interface; Airflow adds scheduling, dependency management, retries and UI.

Airflow runs in `.venv-airflow`, while each task activates `.venv` before
executing the actual project commands. This keeps Airflow dependencies isolated
from dbt/ingestion dependencies.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator


REPO_ROOT = Path(__file__).resolve().parents[3]

PROJECT_ID = "market-data-platform-adam-dev"
RAW_BUCKET = "market-data-platform-adam-dev-raw-dev"
BQ_LOCATION = "europe-west1"
BQ_MAX_BYTES = "52428800"

DEFAULT_ARGS = {
    "owner": "adam",
    "depends_on_past": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=2),
}


def make_task(task_id: str, make_target: str) -> BashOperator:
    return BashOperator(
        task_id=task_id,
        bash_command=(
            f"cd {REPO_ROOT} && "
            f". .venv/bin/activate && "
            f"make {make_target}"
        ),
        env={
            "PYTHONUNBUFFERED": "1",
            "PROJECT_ID": PROJECT_ID,
            "RAW_BUCKET": RAW_BUCKET,
            "BQ_LOCATION": BQ_LOCATION,
            "BQ_MAX_BYTES": BQ_MAX_BYTES,
        },
        append_env=True,
    )


with DAG(
    dag_id="market_data_platform_dev",
    description="Local orchestration DAG for ingestion, BigQuery load, dbt build and validation.",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
    tags=["market-data-platform", "dev", "local"],
) as dag:
    check_env = make_task("check_env", "check-env")
    test = make_task("test", "test")
    ingest_backfill = make_task("ingest_backfill", "ingest-backfill")
    load_bq_raw = make_task("load_bq_raw", "load-bq-raw")
    dbt_build = make_task("dbt_build", "dbt-build")
    validate_raw = make_task("validate_raw", "validate-raw")
    validate_marts = make_task("validate_marts", "validate-marts")
    cost_check = make_task("cost_check", "cost-check")

    check_env >> test >> ingest_backfill >> load_bq_raw >> dbt_build
    dbt_build >> [validate_raw, validate_marts] >> cost_check
