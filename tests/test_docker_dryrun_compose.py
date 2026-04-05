from pathlib import Path

import yaml


def test_compose_contains_executor_and_jesse_dryrun_services():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())

    services = compose["services"]

    assert "executor" in services
    assert "jesse-dryrun" in services


def test_executor_and_jesse_dryrun_use_postgres_hostname_and_healthchecks():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())
    services = compose["services"]

    executor = services["executor"]
    dryrun = services["jesse-dryrun"]

    assert executor["environment"]["POSTGRES_HOST"] == "postgres"
    assert dryrun["environment"]["POSTGRES_HOST"] == "postgres"
    assert executor["environment"]["PYTHONPATH"] == "/app"
    assert dryrun["environment"]["PYTHONPATH"] == "/app"
    assert "healthcheck" in executor
    assert "healthcheck" in dryrun


def test_compose_dryrun_minimal_stack_does_not_include_legacy_services():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())
    services = compose["services"]

    assert "signal-service" not in services
    assert "executor-service" not in services


def test_compose_contains_db_init_service_and_dryrun_services_depend_on_it():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())
    services = compose["services"]

    assert "db-init" in services
    assert services["executor"]["depends_on"]["db-init"]["condition"] == "service_completed_successfully"
    assert services["jesse-dryrun"]["depends_on"]["db-init"]["condition"] == "service_completed_successfully"
