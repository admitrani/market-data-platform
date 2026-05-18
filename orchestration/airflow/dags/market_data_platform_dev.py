"""Local Airflow DAG for the Market Data Platform dev pipeline.

The DAG orchestrates Makefile targets instead of duplicating business logic.
Configuration is read from config/pipeline_dev.env so Airflow and Makefile share
the same runtime parameters.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator


REPO_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_CONFIG_PATH = REPO_ROOT / "config" / "pipeline_dev.env"


def load_env_file(path: Path) -> dict[str, str]:
    """Load simple KEY=VALUE config files without adding extra dependencies."""

    values: dict[str, str] = {}

    if not path.exists():
        raise FileNotFoundError(f"Pipeline config file not found: {path}")

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            raise ValueError(f"Invalid config line in {path}: {raw_line}")

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    return values


PIPELINE_ENV = load_env_file(PIPELINE_CONFIG_PATH)

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
            **PIPELINE_ENV,
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
