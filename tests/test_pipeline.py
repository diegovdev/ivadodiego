"""Unit tests for pipeline — V6, V16, V17."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import museums.db as db
import museums.enricher as enricher_mod
import museums.pipeline as pipeline
import museums.scraper as scraper_mod
from museums.db import Base, CityRow, MuseumRow
from museums.enricher import CityRecord
from museums.scraper import MuseumRecord

_MUSEUMS = [
    MuseumRecord(name="Louvre", city="Paris", country="France", visitors_annual=9_000_000),
    MuseumRecord(
        name="British Museum", city="London", country="UK", visitors_annual=6_000_000
    ),
]
_CITIES = [
    CityRecord(name="Paris", country="France", population=2_161_000),
    CityRecord(name="London", country="UK", population=8_982_000),
]


@pytest.fixture(autouse=True)
def reset_pipeline_state() -> Generator[None, None, None]:
    pipeline._ingest_result = pipeline._RunResult()
    pipeline._train_result = pipeline._RunResult()
    yield


@pytest.fixture()
def patched_db(monkeypatch: pytest.MonkeyPatch) -> Generator[sessionmaker, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db, "_session_factory", factory)
    yield factory


@pytest.fixture()
def populated_db(
    monkeypatch: pytest.MonkeyPatch, patched_db: sessionmaker
) -> sessionmaker:
    monkeypatch.setattr(scraper_mod, "fetch_museums", lambda: _MUSEUMS)
    monkeypatch.setattr(enricher_mod, "fetch_city_populations", lambda names: _CITIES)
    pipeline.run_ingest()
    return patched_db


# V16: ingest writes museums and cities to DB
def test_run_ingest_populates_db(
    monkeypatch: pytest.MonkeyPatch, patched_db: sessionmaker
) -> None:
    monkeypatch.setattr(scraper_mod, "fetch_museums", lambda: _MUSEUMS)
    monkeypatch.setattr(enricher_mod, "fetch_city_populations", lambda names: _CITIES)
    pipeline.run_ingest()
    session: Session = patched_db()
    try:
        museum_rows = session.execute(select(MuseumRow)).scalars().all()
        city_rows = session.execute(select(CityRow)).scalars().all()
    finally:
        session.close()
    assert len(museum_rows) == 2
    assert len(city_rows) == 2


# V16: calling ingest twice produces no duplicate rows
def test_run_ingest_idempotent(
    monkeypatch: pytest.MonkeyPatch, patched_db: sessionmaker
) -> None:
    monkeypatch.setattr(scraper_mod, "fetch_museums", lambda: _MUSEUMS)
    monkeypatch.setattr(enricher_mod, "fetch_city_populations", lambda names: _CITIES)
    pipeline.run_ingest()
    pipeline.run_ingest()
    session: Session = patched_db()
    try:
        museum_rows = session.execute(select(MuseumRow)).scalars().all()
        city_rows = session.execute(select(CityRow)).scalars().all()
    finally:
        session.close()
    assert len(museum_rows) == 2
    assert len(city_rows) == 2


# V6: ingest success sets status "ok"
def test_run_ingest_status_ok(
    monkeypatch: pytest.MonkeyPatch, patched_db: sessionmaker
) -> None:
    monkeypatch.setattr(scraper_mod, "fetch_museums", lambda: _MUSEUMS)
    monkeypatch.setattr(enricher_mod, "fetch_city_populations", lambda names: _CITIES)
    pipeline.run_ingest()
    status = pipeline.last_ingest_status()
    assert status["status"] == "ok"
    assert status["last_run"] is not None


# error path sets status "error" without raising
def test_run_ingest_status_error(
    monkeypatch: pytest.MonkeyPatch, patched_db: sessionmaker
) -> None:
    def _fail() -> list:
        raise RuntimeError("scraper down")

    monkeypatch.setattr(scraper_mod, "fetch_museums", _fail)
    pipeline.run_ingest()
    status = pipeline.last_ingest_status()
    assert status["status"] == "error"
    assert "scraper down" in str(status["detail"])


# V17: empty DB → InsufficientDataError caught → status "skipped"
def test_run_train_insufficient_data(patched_db: sessionmaker) -> None:
    pipeline.run_train()
    status = pipeline.last_train_status()
    assert status["status"] == "skipped"
    assert status["last_run"] is not None


# V18: populated DB → train succeeds → status "ok", R² in detail
def test_run_train_ok(
    tmp_path: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    populated_db: sessionmaker,
) -> None:
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "regression.pkl"))
    pipeline.run_train()
    status = pipeline.last_train_status()
    assert status["status"] == "ok"
    assert "R²" in str(status["detail"])
