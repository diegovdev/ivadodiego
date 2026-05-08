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
from museums.db import SessionDep, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        init_db(database_url)
    try:
        regression.load_model()
    except Exception as exc:
        logger.warning("model not loaded at startup: %s", exc)
    yield


app = FastAPI(title="Museums API", lifespan=lifespan)


class HealthResponse(BaseModel):
    status: str


class Museum(BaseModel):
    id: int
    name: str
    city: str
    country: str
    visitors_annual: int


class City(BaseModel):
    id: int
    name: str
    country: str
    population: int


class PredictRequest(BaseModel):
    population: int = Field(ge=0)


class PredictResponse(BaseModel):
    predicted_visitors: int


class StatusResponse(BaseModel):
    status: str


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/museums", response_model=list[Museum])
def list_museums(session: SessionDep) -> list[Museum]:
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
def get_museum(museum_id: int, session: SessionDep) -> Museum:
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
def list_cities(session: SessionDep) -> list[City]:
    rows = db.get_all_cities(session)
    return [
        City(id=row.id, name=row.name, country=row.country, population=row.population)
        for row in rows
    ]


@app.post("/predict", response_model=PredictResponse)
def predict(body: PredictRequest) -> PredictResponse:
    try:
        result = regression.predict(body.population)
    except regression.ModelNotLoadedError:
        raise HTTPException(status_code=400, detail="model not available")
    return PredictResponse(predicted_visitors=result)


@app.post("/ingest", response_model=StatusResponse, status_code=HTTPStatus.ACCEPTED)
def ingest() -> StatusResponse:
    return StatusResponse(status="accepted")


@app.post("/train", response_model=StatusResponse, status_code=HTTPStatus.ACCEPTED)
def train() -> StatusResponse:
    return StatusResponse(status="accepted")
