import logging
import os
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session, sessionmaker

import museums.regression as reg_module
from museums.db import Base, get_engine, upsert_city, upsert_museum
from museums.regression import InsufficientDataError, predict, train

_URL = "sqlite:///:memory:"


@pytest.fixture()
def session() -> Generator[Session, None, None]:
    engine = get_engine(_URL)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    s = factory()
    try:
        yield s
        s.commit()
    finally:
        s.close()


def _seed(
    session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "model.pkl"))
    upsert_city(session, "Paris", "France", 2_000_000)
    upsert_city(session, "London", "United Kingdom", 9_000_000)
    upsert_museum(session, "Louvre", "Paris", "France", 9_000_000)
    upsert_museum(session, "British Museum", "London", "United Kingdom", 6_000_000)
    session.commit()


# V17: fewer than 2 distinct city populations → InsufficientDataError
def test_train_insufficient_data(
    session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "model.pkl"))
    upsert_city(session, "Paris", "France", 2_000_000)
    upsert_museum(session, "Louvre", "Paris", "France", 9_000_000)
    session.commit()
    with pytest.raises(InsufficientDataError):
        train(session)


# V18: R² logged at INFO after train
def test_train_logs_r2(
    session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _seed(session, tmp_path, monkeypatch)
    with caplog.at_level(logging.INFO, logger="museums.regression"):
        train(session)
    assert any("R²" in r.message for r in caplog.records)


# V8: predict clamps negative predictions to 0
def test_predict_clamps_negative(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_model = MagicMock()
    mock_model.predict.return_value = [-100.0]
    monkeypatch.setattr(reg_module, "_model", mock_model)
    assert predict(1_000_000) == 0


# V9: joblib file persisted at MODEL_PATH after train
def test_model_persisted(
    session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed(session, tmp_path, monkeypatch)
    train(session)
    path = Path(os.environ["MODEL_PATH"])
    assert path.exists()
    assert path.stat().st_size > 0
