"""FastAPI HTTP surface: health, museums/cities reads, predict, ingest, train, and status."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from http import HTTPStatus

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

import museums.db as db
import museums.pipeline as pipeline
import museums.regression as regression

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialise the DB and load the model on startup.

    Falls back to a local SQLite file when DATABASE_URL is unset so that
    GET endpoints return [] instead of 500 in development.
    """
    database_url = os.environ.get("DATABASE_URL") or "sqlite:///./museums.db"
    db.init_db(database_url)
    try:
        regression.load_model()
    except Exception as exc:
        logger.warning("model not loaded at startup: %s", exc)
    yield


app = FastAPI(title="Museums API", lifespan=lifespan)


class HealthResponse(BaseModel):
    """Health probe payload."""

    status: str


class Museum(BaseModel):
    """Museum DTO returned by the read endpoints."""

    id: int
    name: str
    city: str
    country: str
    visitors_annual: int


class City(BaseModel):
    """City DTO returned by the read endpoints."""

    id: int
    name: str
    country: str
    population: int


class PredictRequest(BaseModel):
    """POST /predict input: a non-negative city population."""

    population: int = Field(ge=0)


class PredictResponse(BaseModel):
    """POST /predict output: predicted annual visitors, clamped to >= 0."""

    predicted_visitors: int = Field(ge=0)


class StatusResponse(BaseModel):
    """Generic status payload for fire-and-forget endpoints."""

    status: str


class PipelineStatus(BaseModel):
    """Status of a single pipeline run (ingest or train)."""

    last_run: datetime | None
    status: str
    detail: str


class StatusReport(BaseModel):
    """GET /status payload: last result for each pipeline."""

    ingest: PipelineStatus
    train: PipelineStatus


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect bare / to the Swagger UI at /docs."""
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe — always returns status=ok if the process is up."""
    return HealthResponse(status="ok")


@app.get("/museums", response_model=list[Museum])
def list_museums(session: db.SessionDep) -> list[Museum]:
    """Return every museum row in the database."""
    rows = db.get_all_museums(session)
    return [
        Museum(
            id=row.id,
            name=row.name,
            city=row.city,
            country=row.country,
            visitors_annual=row.visitors_annual,
        )
        for row in rows
    ]


@app.get("/museums/{museum_id}", response_model=Museum)
def get_museum(museum_id: int, session: db.SessionDep) -> Museum:
    """Return one museum by primary key, or 404 if absent."""
    row = db.get_museum_by_id(session, museum_id)
    if row is None:
        raise HTTPException(status_code=404, detail="not found")
    return Museum(
        id=row.id,
        name=row.name,
        city=row.city,
        country=row.country,
        visitors_annual=row.visitors_annual,
    )


@app.get("/cities", response_model=list[City])
def list_cities(session: db.SessionDep) -> list[City]:
    """Return every city row in the database."""
    rows = db.get_all_cities(session)
    return [
        City(id=row.id, name=row.name, country=row.country, population=row.population)
        for row in rows
    ]


@app.post("/predict", response_model=PredictResponse)
def predict(body: PredictRequest) -> PredictResponse:
    """Predict annual visitors from a city population. 400 if no model is loaded."""
    try:
        result = regression.predict(body.population)
    except regression.ModelNotLoadedError:
        raise HTTPException(status_code=400, detail="model not available")
    return PredictResponse(predicted_visitors=result)


@app.get("/status", response_model=StatusReport)
def pipeline_status() -> StatusReport:
    """Return the last result of each pipeline run (ingest and train)."""
    return StatusReport(
        ingest=PipelineStatus(**pipeline.last_ingest_status()),
        train=PipelineStatus(**pipeline.last_train_status()),
    )


@app.post("/ingest", response_model=StatusResponse, status_code=HTTPStatus.ACCEPTED)
def ingest(background_tasks: BackgroundTasks) -> StatusResponse:
    """Enqueue a scrape + enrich + DB upsert run; returns 202 immediately."""
    background_tasks.add_task(pipeline.run_ingest)
    return StatusResponse(status="accepted")


@app.post("/train", response_model=StatusResponse, status_code=HTTPStatus.ACCEPTED)
def train(background_tasks: BackgroundTasks) -> StatusResponse:
    """Enqueue a regression retrain against the current DB; returns 202 immediately."""
    background_tasks.add_task(pipeline.run_train)
    return StatusResponse(status="accepted")
