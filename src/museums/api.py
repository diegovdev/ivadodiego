"""FastAPI HTTP surface: health, museums/cities reads, predict, and ingest/train stubs."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

import museums.db as db
import museums.regression as regression

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialise the DB (if DATABASE_URL is set) and load the model on startup."""
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
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


@app.post("/ingest", response_model=StatusResponse, status_code=HTTPStatus.ACCEPTED)
def ingest() -> StatusResponse:
    """Trigger a scrape + enrich + DB upsert run. Stub — wiring lands in T12."""
    return StatusResponse(status="accepted")


@app.post("/train", response_model=StatusResponse, status_code=HTTPStatus.ACCEPTED)
def train() -> StatusResponse:
    """Trigger a regression retrain against the current DB. Stub — wiring lands in T12."""
    return StatusResponse(status="accepted")
