import logging
from http import HTTPStatus

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

app = FastAPI(title="Museums API")


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
def list_museums() -> list[Museum]:
    return []


@app.get("/museums/{museum_id}", response_model=Museum)
def get_museum(museum_id: int) -> Museum:
    raise HTTPException(status_code=404, detail="not found")


@app.get("/cities", response_model=list[City])
def list_cities() -> list[City]:
    return []


@app.post("/predict", response_model=PredictResponse)
def predict(body: PredictRequest) -> PredictResponse:
    raise HTTPException(status_code=400, detail="model not available")


@app.post("/ingest", response_model=StatusResponse, status_code=HTTPStatus.ACCEPTED)
def ingest() -> StatusResponse:
    return StatusResponse(status="accepted")


@app.post("/train", response_model=StatusResponse, status_code=HTTPStatus.ACCEPTED)
def train() -> StatusResponse:
    return StatusResponse(status="accepted")
