"""Orchestration: scraper → enricher → db (ingest) and regression.train (train)."""

import logging
from dataclasses import dataclass
from datetime import datetime

import museums.db as db
import museums.enricher as enricher
import museums.regression as regression
import museums.scraper as scraper

logger = logging.getLogger(__name__)


@dataclass
class _RunResult:
    last_run: datetime | None = None
    status: str = "never"
    detail: str = ""


_ingest_result = _RunResult()
_train_result = _RunResult()


def last_ingest_status() -> dict[str, datetime | str | None]:
    return {
        "last_run": _ingest_result.last_run,
        "status": _ingest_result.status,
        "detail": _ingest_result.detail,
    }


def last_train_status() -> dict[str, datetime | str | None]:
    return {
        "last_run": _train_result.last_run,
        "status": _train_result.status,
        "detail": _train_result.detail,
    }


def run_ingest() -> None:
    session = db.new_session()
    try:
        museums_data = scraper.fetch_museums()
        city_names = list({m.city for m in museums_data})
        cities = enricher.fetch_city_populations(city_names)
        for m in museums_data:
            db.upsert_museum(session, m.name, m.city, m.country, m.visitors_annual)
        for c in cities:
            db.upsert_city(session, c.name, c.country, c.population)
        session.commit()
        detail = f"{len(museums_data)} museums, {len(cities)} cities"
        _ingest_result.last_run = datetime.now()
        _ingest_result.status = "ok"
        _ingest_result.detail = detail
        logger.info("ingest complete: %s", detail)
    except Exception as exc:
        session.rollback()
        _ingest_result.last_run = datetime.now()
        _ingest_result.status = "error"
        _ingest_result.detail = str(exc)
        logger.exception("ingest failed")
    finally:
        session.close()


def run_train() -> None:
    session = db.new_session()
    try:
        r2 = regression.train(session)
        _train_result.last_run = datetime.now()
        _train_result.status = "ok"
        _train_result.detail = f"R²={r2:.4f}"
        logger.info("train complete: R²=%.4f", r2)
    except regression.InsufficientDataError as exc:
        session.rollback()
        _train_result.last_run = datetime.now()
        _train_result.status = "skipped"
        _train_result.detail = str(exc)
        logger.warning("train skipped: %s", exc)
    except Exception as exc:
        session.rollback()
        _train_result.last_run = datetime.now()
        _train_result.status = "error"
        _train_result.detail = str(exc)
        logger.exception("train failed")
    finally:
        session.close()
