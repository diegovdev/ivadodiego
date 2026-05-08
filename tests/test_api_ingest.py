"""Tests for POST /ingest wiring: V16 idempotency and V6 HTTP mocking."""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import museums.db as db
from museums.api import app
from museums.db import Base, CityRow, MuseumRow

_WIKI_HTML = (Path(__file__).parent / "fixtures" / "wikipedia_museums.html").read_text(
    encoding="utf-8"
)

_WIKIDATA_RESPONSE = {
    "results": {
        "bindings": [
            {
                "name": {"value": "Paris"},
                "countryLabel": {"value": "France"},
                "population": {"value": "2161000"},
            },
            {
                "name": {"value": "London"},
                "countryLabel": {"value": "United Kingdom"},
                "population": {"value": "8982000"},
            },
        ]
    }
}


@pytest.fixture()
def client_and_session(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TestClient, Session], None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db, "_session_factory", factory)
    session = factory()
    with TestClient(app) as c:
        yield c, session
    session.close()


# V16: ingest is idempotent — second run produces same row count
def test_ingest_is_idempotent(
    client_and_session: tuple[TestClient, Session],
    httpx_mock: HTTPXMock,
) -> None:
    client, session = client_and_session
    httpx_mock.add_response(text=_WIKI_HTML)
    httpx_mock.add_response(json=_WIKIDATA_RESPONSE)
    client.post("/ingest")
    count_museums_1 = len(session.execute(select(MuseumRow)).scalars().all())
    count_cities_1 = len(session.execute(select(CityRow)).scalars().all())

    httpx_mock.add_response(text=_WIKI_HTML)
    httpx_mock.add_response(json=_WIKIDATA_RESPONSE)
    client.post("/ingest")
    count_museums_2 = len(session.execute(select(MuseumRow)).scalars().all())
    count_cities_2 = len(session.execute(select(CityRow)).scalars().all())

    assert count_museums_1 == count_museums_2
    assert count_cities_1 == count_cities_2


# V6: POST /ingest returns 202 and all HTTP is mocked (no live calls)
def test_ingest_mocks_http(
    client_and_session: tuple[TestClient, Session],
    httpx_mock: HTTPXMock,
) -> None:
    client, _ = client_and_session
    httpx_mock.add_response(text=_WIKI_HTML)
    httpx_mock.add_response(json=_WIKIDATA_RESPONSE)
    r = client.post("/ingest")
    assert r.status_code == 202
    assert r.json() == {"status": "accepted"}
