"""Local/Docker Airflow DAG for the Market Data Platform dev pipeline.

The DAG orchestrates Makefile targets instead of duplicating business logic.
Configuration is read from config/pipeline_dev.env so Airflow and Makefile share
the same runtime parameters.

Supported runtimes:
- local .venv-airflow + SQLite
- Docker Compose Airflow + Postgres metadata DB

Reliability features:
- retries
- retry delay
- execution timeout per task
- DAG run timeout
- SLA policy
- optional Slack failure callback via SLACK_WEBHOOK_URL
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
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


def config_int(config: dict[str, str], key: str, default: int) -> int:
    raw_value = config.get(key, str(default))

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer, got: {raw_value}") from exc


PIPELINE_ENV = load_env_file(PIPELINE_CONFIG_PATH)

AIRFLOW_RETRIES = config_int(PIPELINE_ENV, "AIRFLOW_RETRIES", 1)
AIRFLOW_RETRY_DELAY_MINUTES = config_int(PIPELINE_ENV, "AIRFLOW_RETRY_DELAY_MINUTES", 2)
AIRFLOW_TASK_TIMEOUT_MINUTES = config_int(PIPELINE_ENV, "AIRFLOW_TASK_TIMEOUT_MINUTES", 20)
AIRFLOW_DAG_TIMEOUT_MINUTES = config_int(PIPELINE_ENV, "AIRFLOW_DAG_TIMEOUT_MINUTES", 45)
AIRFLOW_SLA_MINUTES = config_int(PIPELINE_ENV, "AIRFLOW_SLA_MINUTES", 30)


def notify_failure(context: dict[str, Any]) -> None:
    """Send an optional failure notification.

    The Slack webhook is intentionally read from the runtime environment and is
    never stored in config/pipeline_dev.env or committed to Git.
    """

    task_instance = context.get("task_instance")
    dag_run = context.get("dag_run")
    exception = context.get("exception")

    payload = {
        "dag_id": getattr(task_instance, "dag_id", "unknown"),
        "task_id": getattr(task_instance, "task_id", "unknown"),
        "run_id": getattr(dag_run, "run_id", "unknown"),
        "execution_date": str(context.get("execution_date")),
        "try_number": getattr(task_instance, "try_number", None),
        "log_url": getattr(task_instance, "log_url", None),
        "exception": str(exception) if exception else None,
    }

    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")

    if not webhook_url:
        print("[failure-alert] SLACK_WEBHOOK_URL not set. Payload:")
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return

    message = (
        ":red_circle: Airflow task failed\n"
        f"*DAG*: `{payload['dag_id']}`\n"
        f"*Task*: `{payload['task_id']}`\n"
        f"*Run*: `{payload['run_id']}`\n"
        f"*Try*: `{payload['try_number']}`\n"
        f"*Exception*: `{payload['exception']}`\n"
        f"*Logs*: {payload['log_url']}"
    )

    try:
        response = requests.post(
            webhook_url,
            json={"text": message},
            timeout=10,
        )
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - notification failures must not mask task failure
        print(f"[failure-alert] Failed to send Slack notification: {exc}")
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))


DEFAULT_ARGS = {
    "owner": "adam",
    "depends_on_past": False,
    "retries": AIRFLOW_RETRIES,
    "retry_delay": timedelta(minutes=AIRFLOW_RETRY_DELAY_MINUTES),
    "retry_exponential_backoff": True,
    "email_on_failure": False,
    "email_on_retry": False,
    "on_failure_callback": notify_failure,
}


def make_task(
    task_id: str,
    make_target: str,
    timeout_minutes: int = AIRFLOW_TASK_TIMEOUT_MINUTES,
) -> BashOperator:
    return BashOperator(
        task_id=task_id,
        bash_command=(
            f"cd {REPO_ROOT} && "
            f"if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi && "
            f"make {make_target}"
        ),
        env={
            "PYTHONUNBUFFERED": "1",
            **PIPELINE_ENV,
        },
        append_env=True,
        execution_timeout=timedelta(minutes=timeout_minutes),
        sla=timedelta(minutes=AIRFLOW_SLA_MINUTES),
    )


with DAG(
    dag_id="market_data_platform_dev",
    description="Local/Docker orchestration DAG for ingestion, BigQuery load, dbt run/test/freshness and validation.",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(minutes=AIRFLOW_DAG_TIMEOUT_MINUTES),
    tags=["market-data-platform", "dev", "local", "docker"],
) as dag:
    check_env = make_task("check_env", "check-env", timeout_minutes=5)
    unit_tests = make_task("unit_tests", "test", timeout_minutes=10)

    extract_load_gcs = make_task("extract_load_gcs", "ingest-backfill", timeout_minutes=15)
    load_bq_raw = make_task("load_bq_raw", "load-bq-raw", timeout_minutes=10)

    dbt_run = make_task("dbt_run", "dbt-run", timeout_minutes=20)
    dbt_test = make_task("dbt_test", "dbt-test", timeout_minutes=25)
    dbt_source_freshness = make_task("dbt_source_freshness", "dbt-source-freshness", timeout_minutes=10)

    validate_raw = make_task("validate_raw", "validate-raw", timeout_minutes=5)
    validate_marts = make_task("validate_marts", "validate-marts", timeout_minutes=5)
    cost_check = make_task("cost_check", "cost-check", timeout_minutes=5)

    check_env >> unit_tests >> extract_load_gcs >> load_bq_raw
    load_bq_raw >> dbt_run >> dbt_test >> dbt_source_freshness
    dbt_source_freshness >> [validate_raw, validate_marts] >> cost_check
