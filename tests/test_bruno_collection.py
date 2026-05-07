"""Validate Bruno API collection structure — V29."""
from pathlib import Path

import yaml

API_DIR = Path("tests/api")

REQUIRED_STEMS = {
    "01-get-health", "02-get-museums", "03-get-museum-by-id",
    "04-get-cities", "05-post-predict", "06-post-ingest", "07-post-train",
}


def test_opencollection_manifest_exists() -> None:
    manifest = yaml.safe_load((API_DIR / "opencollection.yml").read_text())
    assert manifest["opencollection"] == "1.0.0"
    assert manifest["info"]["name"] == "Museums API"


def test_environment_file_exists() -> None:
    env = yaml.safe_load((API_DIR / "environments" / "Museums.yml").read_text())
    assert env["name"] == "Museums"
    names = {v["name"] for v in env["variables"]}
    assert "baseUrl" in names


def _request_files() -> list[Path]:
    return sorted(
        f for f in API_DIR.iterdir()
        if f.suffix == ".yml" and f.parent == API_DIR and f.name != "opencollection.yml"
    )


def test_all_routes_have_request_files() -> None:
    stems = {f.stem for f in _request_files()}
    assert REQUIRED_STEMS <= stems


def test_all_request_files_are_valid_yaml() -> None:
    for f in _request_files():
        yaml.safe_load(f.read_text())


def test_all_requests_use_base_url_variable() -> None:
    for f in _request_files():
        assert "{{baseUrl}}" in f.read_text(), f"{f.name} missing {{{{baseUrl}}}}"


def test_all_requests_have_seq_field() -> None:
    for f in _request_files():
        doc = yaml.safe_load(f.read_text())
        assert "seq" in doc.get("info", {}), f"{f.name} missing info.seq"
