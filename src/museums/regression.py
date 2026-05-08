"""Linear regression: train on (population → visitors), persist via joblib, predict."""

import logging
import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session

import museums.db as db

logger = logging.getLogger(__name__)

_model: LinearRegression | None = None


class InsufficientDataError(Exception):
    """Raised when fewer than 2 distinct city populations are available."""


class ModelNotLoadedError(RuntimeError):
    """Raised when predict() is called before the model has been loaded or trained."""


def _model_path() -> Path:
    return Path(os.getenv("MODEL_PATH", "models/regression.pkl"))


def train(session: Session) -> float:
    """Fit LinearRegression on joined museum/city rows, persist to MODEL_PATH, return R².

    Raises:
        InsufficientDataError: if fewer than 2 distinct city populations are present.
    """
    rows = db.get_training_rows(session)
    if len({r.population for r in rows}) < 2:
        raise InsufficientDataError(f"need ≥2 distinct city populations, got {len(rows)} rows")
    X = np.array([[r.population] for r in rows])
    y = np.array([r.visitors_annual for r in rows])
    model = LinearRegression()
    model.fit(X, y)
    r2: float = model.score(X, y)
    path = _model_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    global _model
    _model = model
    logger.info("trained: R²=%.4f n=%d path=%s", r2, len(rows), path)
    return r2


def load_model() -> None:
    """Load the persisted model from MODEL_PATH into the module-level cache."""
    global _model
    path = _model_path()
    _model = joblib.load(path)
    logger.info("model loaded from %s", path)


def predict(population: int) -> int:
    """Predict annual visitors for the given city population, clamped to >= 0.

    Raises:
        ModelNotLoadedError: if neither train() nor load_model() has run.
    """
    if _model is None:
        raise ModelNotLoadedError("model not loaded — call load_model() or train() first")
    pred: float = _model.predict([[population]])[0]
    return max(0, int(pred))
