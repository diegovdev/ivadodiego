from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class InsufficientDataError(Exception):
    """Raised when fewer than 2 distinct samples are available for training."""


def train(session: Session) -> float:
    """Fit regression, persist model, return R²."""
    ...


def predict(population: int) -> int:
    """Return max(0, int(predicted_visitors))."""
    ...
