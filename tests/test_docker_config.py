"""Verify Dockerfile and docker-compose.yml satisfy structural invariants."""
from pathlib import Path

import yaml

_REPO = Path(__file__).parent.parent
DOCKERFILE = (_REPO / "Dockerfile").read_text()
COMPOSE = yaml.safe_load((_REPO / "docker-compose.yml").read_text())


def test_dockerfile_alpine_base() -> None:
    """V37: base image must be python:3.12-alpine."""
    from_lines = [line for line in DOCKERFILE.splitlines() if line.startswith("FROM")]
    assert all("python:3.12-alpine" in line for line in from_lines)


def test_dockerfile_two_stages() -> None:
    """V23: multi-stage build strips dev deps."""
    from_lines = [line for line in DOCKERFILE.splitlines() if line.startswith("FROM")]
    assert len(from_lines) == 2


def test_dockerfile_non_root_user() -> None:
    """V13: runtime stage must run as uid 1000."""
    assert "USER 1000" in DOCKERFILE


def test_compose_jupyter_depends_on_api_healthy() -> None:
    """V14: jupyter must not start until api healthcheck passes."""
    dep = COMPOSE["services"]["jupyter"]["depends_on"]["api"]
    assert dep["condition"] == "service_healthy"


def test_compose_shared_volume() -> None:
    """V21: museums-data volume must be mounted by both services."""
    api_vols = str(COMPOSE["services"]["api"].get("volumes", []))
    jupyter_vols = str(COMPOSE["services"]["jupyter"].get("volumes", []))
    assert "museums-data" in api_vols
    assert "museums-data" in jupyter_vols


def test_compose_volume_declared() -> None:
    """V21: museums-data must be declared as a named volume."""
    assert "museums-data" in COMPOSE.get("volumes", {})
