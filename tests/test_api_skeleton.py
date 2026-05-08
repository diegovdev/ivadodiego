"""API skeleton route shape tests — no ML required."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from museums.api import app
from museums.db import Base, get_session


@pytest.fixture(scope="module")
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture(scope="module")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_museums_returns_list(client: TestClient) -> None:
    r = client.get("/museums")
    assert r.status_code == 200
    assert r.json() == []


def test_museum_not_found(client: TestClient) -> None:
    r = client.get("/museums/999")
    assert r.status_code == 404


def test_cities_returns_list(client: TestClient) -> None:
    r = client.get("/cities")
    assert r.status_code == 200
    assert r.json() == []


def test_predict_no_model_returns_400(client: TestClient) -> None:
    r = client.post("/predict", json={"population": 1000000})
    assert r.status_code == 400


def test_ingest_accepted(client: TestClient) -> None:
    r = client.post("/ingest")
    assert r.status_code == 202
    assert r.json() == {"status": "accepted"}


def test_train_accepted(client: TestClient) -> None:
    r = client.post("/train")
    assert r.status_code == 202
    assert r.json() == {"status": "accepted"}


def test_docs_available(client: TestClient) -> None:
    r = client.get("/docs")
    assert r.status_code == 200


def test_museums_empty_without_database_url() -> None:
    """GET /museums must return 200 [] when DATABASE_URL is unset (no 500)."""
    import os

    env_backup = os.environ.pop("DATABASE_URL", None)
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.get("/museums")
        assert r.status_code == 200
        assert r.json() == []
    finally:
        if env_backup is not None:
            os.environ["DATABASE_URL"] = env_backup
        app.dependency_overrides.clear()
