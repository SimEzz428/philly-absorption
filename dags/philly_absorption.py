from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

PROJECT_DIR = "{{ var.value.get('philly_project_dir', '/opt/philly-absorption') }}"

DEFAULT_ARGS = {
    "owner": "mohamed",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "execution_timeout": timedelta(hours=2),
    "depends_on_past": False,
}


def stage(dag, task_id, script, timeout_hours=2, retries=None):
    args = {}
    if retries is not None:
        args["retries"] = retries
    return BashOperator(
        task_id=task_id,
        bash_command=f"cd {PROJECT_DIR} && python3 {script}",
        execution_timeout=timedelta(hours=timeout_hours),
        dag=dag,
        **args,
    )


with DAG(
    dag_id="philly_absorption",
    description="Permit, deed and assessment ingestion through to submarket ranking",
    schedule="0 6 * * 1",
    start_date=pendulum.datetime(2026, 1, 1, tz="America/New_York"),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["philadelphia", "real-estate", "etl"],
) as dag:

    start = EmptyOperator(task_id="start")

    logic_tests = BashOperator(
        task_id="logic_tests",
        bash_command=(
            f"cd {PROJECT_DIR} && python3 -m pytest -q "
            "-k 'not built' --no-header"
        ),
        execution_timeout=timedelta(minutes=10),
        retries=0,
        dag=dag,
    )

    ingest_permits = stage(dag, "ingest_permits", "ingest_permits.py", 3)
    ingest_deeds = stage(dag, "ingest_deeds", "ingest_rtt.py", 3)
    ingest_assessments = stage(dag, "ingest_assessments", "ingest_opa.py", 3)

    load_postgres = stage(dag, "load_postgres", "load_pg.py", 2)

    build_population = stage(dag, "build_population", "build.py", 2, retries=1)

    invariant_gate = BashOperator(
        task_id="invariant_gate",
        bash_command=(
            f"cd {PROJECT_DIR} && python3 -m pytest -q "
            "-k 'built or Invariants or Leakage' --no-header"
        ),
        execution_timeout=timedelta(minutes=20),
        retries=0,
        dag=dag,
    )

    analyze = stage(dag, "analyze", "analyze.py", 1, retries=1)
    fit_model = stage(dag, "fit_model", "model.py", 2, retries=1)
    tract_comparables = stage(dag, "tract_comparables", "tract_comps.py", 1, retries=1)

    done = EmptyOperator(task_id="done")

    start >> logic_tests
    logic_tests >> [ingest_permits, ingest_deeds, ingest_assessments]
    [ingest_permits, ingest_deeds, ingest_assessments] >> load_postgres
    load_postgres >> build_population >> invariant_gate
    invariant_gate >> [analyze, fit_model, tract_comparables] >> done
