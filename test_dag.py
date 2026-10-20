import os
from datetime import timedelta

os.environ.setdefault("AIRFLOW_HOME", "/tmp/af")
os.environ.setdefault("AIRFLOW__CORE__LOAD_EXAMPLES", "False")

import pytest
from airflow.models import DagBag

DAG_ID = "philly_absorption"
DAG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dags")


@pytest.fixture(scope="module")
def bag():
    return DagBag(dag_folder=DAG_DIR, include_examples=False)


@pytest.fixture(scope="module")
def dag(bag):
    assert bag.import_errors == {}, bag.import_errors
    assert DAG_ID in bag.dags, sorted(bag.dags)
    return bag.dags[DAG_ID]


def ids(tasks):
    return sorted(t.task_id for t in tasks)


def test_dag_imports_without_error(bag):
    assert bag.import_errors == {}


def test_every_expected_stage_is_present(dag):
    assert ids(dag.tasks) == sorted([
        "start", "logic_tests", "ingest_permits", "ingest_deeds",
        "ingest_assessments", "load_postgres", "build_population",
        "invariant_gate", "analyze", "fit_model", "tract_comparables", "done",
    ])


def test_logic_tests_run_before_any_ingestion(dag):
    gate = dag.get_task("logic_tests")
    assert ids(gate.downstream_list) == [
        "ingest_assessments", "ingest_deeds", "ingest_permits"]


def test_the_three_ingests_run_in_parallel(dag):
    for t in ("ingest_permits", "ingest_deeds", "ingest_assessments"):
        task = dag.get_task(t)
        assert ids(task.upstream_list) == ["logic_tests"]
        assert ids(task.downstream_list) == ["load_postgres"]


def test_load_waits_for_all_three_sources(dag):
    assert ids(dag.get_task("load_postgres").upstream_list) == [
        "ingest_assessments", "ingest_deeds", "ingest_permits"]


def test_modelling_is_gated_on_the_invariants(dag):
    gate = dag.get_task("invariant_gate")
    assert ids(gate.upstream_list) == ["build_population"]
    assert ids(gate.downstream_list) == [
        "analyze", "fit_model", "tract_comparables"]


def test_no_modelling_stage_can_bypass_the_gate(dag):
    for t in ("analyze", "fit_model", "tract_comparables"):
        assert ids(dag.get_task(t).upstream_list) == ["invariant_gate"]


def test_gates_never_retry(dag):
    for t in ("logic_tests", "invariant_gate"):
        assert dag.get_task(t).retries == 0


def test_ingestion_retries_with_exponential_backoff(dag):
    for t in ("ingest_permits", "ingest_deeds", "ingest_assessments"):
        task = dag.get_task(t)
        assert task.retries == 3
        assert task.retry_exponential_backoff is True
        assert task.max_retry_delay == timedelta(minutes=30)


def test_runs_are_serialised_and_do_not_backfill(dag):
    assert dag.max_active_runs == 1
    assert dag.catchup is False


def test_every_working_task_has_an_execution_timeout(dag):
    missing = [t.task_id for t in dag.tasks
               if getattr(t, "bash_command", None)
               and t.execution_timeout is None]
    assert missing == []


def test_no_cycles(dag):
    dag.validate()


def test_project_dir_is_not_hardcoded(dag):
    for t in dag.tasks:
        cmd = getattr(t, "bash_command", "") or ""
        if cmd:
            assert "var.value.get" in cmd or "{{" in cmd
            assert "/Users/" not in cmd
