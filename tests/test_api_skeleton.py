"""API skeleton route shape tests — no DB, no ML required."""

from fastapi.testclient import TestClient

from museums.api import app

client = TestClient(app, raise_server_exceptions=False)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_museums_returns_list() -> None:
    r = client.get("/museums")
    assert r.status_code == 200
    assert r.json() == []


def test_museum_not_found() -> None:
    r = client.get("/museums/999")
    assert r.status_code == 404


def test_cities_returns_list() -> None:
    r = client.get("/cities")
    assert r.status_code == 200
    assert r.json() == []


def test_predict_no_model_returns_400() -> None:
    r = client.post("/predict", json={"population": 1000000})
    assert r.status_code == 400


def test_ingest_accepted() -> None:
    r = client.post("/ingest")
    assert r.status_code == 202
    assert r.json() == {"status": "accepted"}


def test_train_accepted() -> None:
    r = client.post("/train")
    assert r.status_code == 202
    assert r.json() == {"status": "accepted"}


def test_docs_available() -> None:
    r = client.get("/docs")
    assert r.status_code == 200
