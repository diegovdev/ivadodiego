"""Validate PR workflow structure — V24, V27, V28."""
from pathlib import Path

import yaml

WF = Path(".github/workflows/pr.yml")


def _jobs() -> dict:
    return yaml.safe_load(WF.read_text()).get("jobs", {})


def test_workflow_exists_and_valid() -> None:
    assert WF.exists()
    yaml.safe_load(WF.read_text())


def test_preflight_job_present() -> None:
    assert "preflight" in _jobs()


def test_matrix_versions() -> None:
    matrix = _jobs()["unit-test"]["strategy"]["matrix"]["python"]
    assert "3.12" in matrix
    assert "3.13" in matrix


def test_all_required_jobs_present() -> None:
    required = {"preflight", "lint", "unit-test", "security-test", "build", "api-test"}
    assert required <= set(_jobs().keys())


def test_heavy_jobs_need_preflight() -> None:
    for job in ("lint", "unit-test", "security-test", "build"):
        needs = _jobs()[job].get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        assert "preflight" in needs, f"{job} must need preflight"


def test_api_test_needs_lint_and_unit_test() -> None:
    needs = _jobs()["api-test"].get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    assert "lint" in needs
    assert "unit-test" in needs
